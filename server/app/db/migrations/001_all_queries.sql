
CREATE EXTENSION IF NOT EXISTS "plpgsql";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS ai CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;


-- ============================================================================
-- USERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email          TEXT UNIQUE NOT NULL,
    password_hash  TEXT,            -- Nullable for OAuth-only
    full_name      TEXT,
    avatar_url     TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================================
-- OAUTH PROVIDERS (lookup table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_provider (
    provider_code    TEXT PRIMARY KEY,        -- e.g. 'github', 'google'
    provider_name    TEXT NOT NULL,           -- e.g. 'GitHub'
    issuer_url       TEXT
);

-- ============================================================================
-- USER-OAUTH ACCOUNTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_oauth_account (
    user_id             UUID REFERENCES users(user_id) ON DELETE CASCADE,
    provider_code       TEXT REFERENCES oauth_provider(provider_code) NOT NULL,
    provider_uid        TEXT NOT NULL,    -- external user ID from provider
    access_token        TEXT,
    refresh_token       TEXT,
    scope               TEXT[],
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, provider_code),
    UNIQUE (provider_code, provider_uid)
);

CREATE INDEX IF NOT EXISTS idx_user_oauth_provider_code ON user_oauth_account(provider_code);

-- ============================================================================
-- REPOSITORIES
-- ============================================================================
CREATE TABLE IF NOT EXISTS repository (
    repo_id             BIGINT PRIMARY KEY,
    node_id             TEXT UNIQUE NOT NULL,
    repo_name           TEXT NOT NULL,
    full_name           TEXT UNIQUE NOT NULL,
    owner_login         TEXT NOT NULL,
    owner_type          TEXT CHECK (owner_type IN ('user', 'organization')) NOT NULL,
    is_private          BOOLEAN NOT NULL DEFAULT FALSE,
    default_branch      TEXT,
    description         TEXT,
    main_language       TEXT,
    topics              TEXT[],
    homepage_url        TEXT,
    license_info        JSONB,
    stargazers_count    INT DEFAULT 0,
    forks_count         INT DEFAULT 0,
    created_at_gh       TIMESTAMPTZ,
    updated_at_gh       TIMESTAMPTZ,
    pushed_at_gh        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repository_owner_login ON repository(owner_login);

-- ============================================================================
-- USER-REPOSITORY RELATIONSHIP
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_repository (
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id         BIGINT REFERENCES repository(repo_id) ON DELETE CASCADE,
    relationship    TEXT CHECK (relationship IN ('owner','collaborator','contributor')),
    PRIMARY KEY(user_id, repo_id)
);

-- ============================================================================
-- GITHUB EVENTS (TIMESCALEDB Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS github_event (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id             BIGINT REFERENCES repository(repo_id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,
    event_id_gh         BIGINT,
    payload             JSONB NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL,
    is_processed        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('github_event', 'occurred_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_github_event_user_time ON github_event(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_github_event_repo_time ON github_event(repo_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_github_event_type_time ON github_event(event_type, occurred_at DESC);

-- ============================================================================
-- CODE CHANGES
-- ============================================================================
CREATE TABLE IF NOT EXISTS code_change (
    change_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id            UUID REFERENCES github_event(event_id) ON DELETE CASCADE,
    sha                 TEXT,
    patch               TEXT,
    files_changed       JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SUMMARIES (AI-generated, PGVECTOR + PGAI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS event_summary (
    summary_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id            UUID REFERENCES github_event(event_id) ON DELETE CASCADE,
    occurred_at         TIMESTAMPTZ NOT NULL,
    summary_text        TEXT NOT NULL,
    tech_stack          TEXT[],
    embedding           VECTOR(1536),     -- pgvector
    ai_model            TEXT,             -- optional, track pgai model used
    ai_tokens           INT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_summary_embedding
    ON event_summary USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- ENUM FOR POST TARGETS
-- ============================================================================
DO $$
BEGIN
    CREATE TYPE post_target AS ENUM ('twitter', 'linkedin', 'journal', 'resume');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;

-- ============================================================================
-- POSTS (Generated social posts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_post (
    post_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id         BIGINT REFERENCES repository(repo_id),
    event_ids       UUID[] NOT NULL,
    content_md      TEXT NOT NULL,
    target          post_target NOT NULL,
    status          TEXT CHECK (status IN ('draft', 'published', 'archived')) DEFAULT 'draft',
    context_hash    UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_post_target ON user_post(user_id, target, created_at DESC);

-- ============================================================================
-- RESUME BULLETS
-- ============================================================================
CREATE TABLE IF NOT EXISTS resume_bullet (
    bullet_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id         BIGINT REFERENCES repository(repo_id),
    event_ids       UUID[] NOT NULL,
    bullet_latex    TEXT NOT NULL,
    keywords        TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POST TEMPLATES
-- ============================================================================
CREATE TABLE IF NOT EXISTS post_template (
    template_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    target          post_target NOT NULL,
    template_name   TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    is_default      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CONTEXT STATE
-- ============================================================================
CREATE TABLE IF NOT EXISTS post_context (
    context_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id         BIGINT REFERENCES repository(repo_id),
    target          post_target NOT NULL,
    last_event_at   TIMESTAMPTZ,
    last_post_id    UUID REFERENCES user_post(post_id),
    UNIQUE (user_id, repo_id, target)
);

-- ============================================================================
-- WEBHOOKS
-- ============================================================================
CREATE TABLE IF NOT EXISTS repo_webhook (
    webhook_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id            UUID REFERENCES users(user_id) ON DELETE CASCADE,
    repo_id            BIGINT REFERENCES repository(repo_id) ON DELETE CASCADE,
    github_webhook_id  BIGINT UNIQUE NOT NULL,
    url                TEXT NOT NULL,
    secret             TEXT NOT NULL,
    events             TEXT[] NOT NULL,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repo_webhook_user ON repo_webhook(user_id);
CREATE INDEX IF NOT EXISTS idx_repo_webhook_repo ON repo_webhook(repo_id);

-- ============================================================================
-- TRIGGERS FOR updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_users_updated_at'
    ) THEN
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_repository_updated_at'
    ) THEN
        CREATE TRIGGER trg_repository_updated_at
            BEFORE UPDATE ON repository
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_user_oauth_account_updated_at'
    ) THEN
        CREATE TRIGGER trg_user_oauth_account_updated_at
            BEFORE UPDATE ON user_oauth_account
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;


