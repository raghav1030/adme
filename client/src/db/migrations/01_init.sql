-- =====================
-- EXTENSIONS
-- =====================
CREATE EXTENSION IF NOT EXISTS "plpgsql";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS ai CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =====================
-- USER (Better Auth style + extra fields)
-- =====================
CREATE TABLE IF NOT EXISTS "user" (
    "id"             TEXT PRIMARY KEY, -- TEXT for Better Auth compatibility
    "email"          TEXT UNIQUE NOT NULL,
    "emailVerified"  BOOLEAN NOT NULL DEFAULT FALSE,
    "passwordHash"   TEXT,
    "name"           TEXT NOT NULL,
    "image"          TEXT,
    "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"("email");

-- =====================
-- SESSION
-- =====================
CREATE TABLE IF NOT EXISTS "session" (
    "id"         TEXT PRIMARY KEY,
    "userId"     TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
    "token"      TEXT UNIQUE NOT NULL,
    "expiresAt"  TIMESTAMPTZ NOT NULL,
    "ipAddress"  TEXT,
    "userAgent"  TEXT,
    "createdAt"  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_session_userId ON "session"("userId");

-- =====================
-- ACCOUNT
-- =====================
CREATE TABLE IF NOT EXISTS "account" (
    "id"                    TEXT PRIMARY KEY,
    "userId"                TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
    "accountId"             TEXT NOT NULL,
    "providerId"            TEXT NOT NULL,
    "accessToken"           TEXT,
    "refreshToken"          TEXT,
    "idToken"               TEXT,
    "accessTokenExpiresAt"  TIMESTAMPTZ,
    "refreshTokenExpiresAt" TIMESTAMPTZ,
    "scope"                 TEXT,
    "password"              TEXT,
    "createdAt"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "last_event_id_gh"      BIGINT,
    "last_event_fetch"      TIMESTAMPTZ,
    "account_username"      TEXT,
    "account_name"          TEXT,
    "account_bio"           TEXT,
    UNIQUE("providerId", "accountId")
);
CREATE INDEX IF NOT EXISTS idx_account_providerId ON "account"("providerId");

-- =====================
-- VERIFICATION
-- =====================
CREATE TABLE IF NOT EXISTS "verification" (
    "id"          TEXT PRIMARY KEY,
    "identifier"  TEXT NOT NULL,
    "value"       TEXT NOT NULL,
    "expiresAt"   TIMESTAMPTZ NOT NULL,
    "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verification_identifier ON "verification"("identifier");

-- =====================
-- OAUTH PROVIDERS
-- =====================
CREATE TABLE IF NOT EXISTS "oauth_provider" (
    "provider_code" TEXT PRIMARY KEY,
    "provider_name" TEXT NOT NULL,
    "issuer_url"    TEXT
);

-- =====================
-- REPOSITORY
-- =====================
CREATE TABLE IF NOT EXISTS "repository" (
    "repo_id"        BIGINT PRIMARY KEY,
    "node_id"        TEXT UNIQUE NOT NULL,
    "repo_name"      TEXT NOT NULL,
    "full_name"      TEXT UNIQUE NOT NULL,
    "owner_login"    TEXT NOT NULL,
    "owner_type"     TEXT CHECK ("owner_type" IN ('user', 'organization')) NOT NULL,
    "is_private"     BOOLEAN NOT NULL DEFAULT FALSE,
    "default_branch" TEXT,
    "description"    TEXT,
    "main_language"  TEXT,
    "topics"         TEXT[],
    "homepage_url"   TEXT,
    "license_info"   JSONB,
    "stargazers_count" INT DEFAULT 0,
    "forks_count"      INT DEFAULT 0,
    "created_at_gh"    TIMESTAMPTZ,
    "updated_at_gh"    TIMESTAMPTZ,
    "pushed_at_gh"     TIMESTAMPTZ,
    "createdAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_repository_owner_login ON "repository"("owner_login");

-- =====================
-- USER-REPOSITORY RELATIONSHIP
-- =====================
CREATE TABLE IF NOT EXISTS "user_repository" (
    "userId"       TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"      BIGINT REFERENCES "repository"("repo_id") ON DELETE CASCADE,
    "relationship" TEXT CHECK ("relationship" IN ('owner','collaborator','contributor')),
    PRIMARY KEY("userId", "repo_id")
);

-- =====================
-- USER POLLING STATE (dynamic)
-- =====================
CREATE TABLE IF NOT EXISTS "user_polling_state" (
    "userId"            TEXT PRIMARY KEY REFERENCES "user"("id") ON DELETE CASCADE,
    "last_event_fetch"  TIMESTAMPTZ,
    "last_event_id_gh"  BIGINT,
    "polling_interval"  INTERVAL DEFAULT interval '6 hours',
    "next_scheduled_at" TIMESTAMPTZ,
    "priority"          SMALLINT DEFAULT 3,
    "source"            TEXT CHECK (source IN ('cron','manual','webhook','login')),
    "etag"              TEXT,
    "updatedAt"         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_polling_next_scheduled
    ON "user_polling_state"(next_scheduled_at);

-- =====================
-- GITHUB EVENTS
-- =====================
-- =====================
-- GITHUB EVENTS
-- =====================
CREATE TABLE IF NOT EXISTS "github_event" (
    "event_id"       UUID DEFAULT uuid_generate_v4(),
    "occurred_at"    TIMESTAMPTZ NOT NULL,
    "userId"         TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"        BIGINT REFERENCES "repository"("repo_id") ON DELETE CASCADE,
    "event_type"     TEXT NOT NULL,
    "event_id_gh"    BIGINT,
    "payload"        JSONB NOT NULL,
    "is_processed"   BOOLEAN NOT NULL DEFAULT FALSE,
    "summary_status" TEXT CHECK ("summary_status" IN ('pending','processing','done','error')) DEFAULT 'pending',
    "fetched_at"     TIMESTAMPTZ DEFAULT NOW(),
    "source"         TEXT CHECK (source IN ('cron','manual','webhook')),
    "createdAt"      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY ("event_id", "occurred_at")
);

-- Turn into a TimescaleDB hypertable
SELECT create_hypertable('github_event', 'occurred_at', if_not_exists => TRUE);

-- ✅ Unique index for deduplication that includes the partition key `occurred_at`
CREATE UNIQUE INDEX IF NOT EXISTS unique_github_event_user_event
    ON github_event ("userId", "event_id_gh", "occurred_at");

CREATE INDEX IF NOT EXISTS idx_github_event_user_time
    ON "github_event"("userId", "occurred_at" DESC);

CREATE INDEX IF NOT EXISTS idx_github_event_repo_time
    ON "github_event"("repo_id", "occurred_at" DESC);

CREATE INDEX IF NOT EXISTS idx_github_event_type_time
    ON "github_event"("event_type", "occurred_at" DESC);

-- =====================
-- CODE CHANGES
-- =====================
CREATE TABLE IF NOT EXISTS "code_change" (
    "change_id"     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "event_id"      UUID NOT NULL,
    "occurred_at"   TIMESTAMPTZ NOT NULL,
    "sha"           TEXT,
    "patch"         TEXT,
    "files_changed" JSONB,
    "createdAt"     TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY ("event_id", "occurred_at") REFERENCES "github_event"("event_id", "occurred_at") ON DELETE CASCADE
);

-- =====================
-- EVENT SUMMARIES
-- =====================
CREATE TABLE IF NOT EXISTS "event_summary" (
    "summary_id"   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "event_id"     UUID NOT NULL,
    "occurred_at"  TIMESTAMPTZ NOT NULL,
    "summary_text" TEXT NOT NULL,
    "tech_stack"   TEXT[],
    "embedding"    VECTOR(1536),
    "ai_model"     TEXT,
    "ai_tokens"    INT,
    "createdAt"    TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY ("event_id", "occurred_at") REFERENCES "github_event" ("event_id", "occurred_at") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_event_summary_embedding
    ON "event_summary" USING ivfflat ("embedding" vector_cosine_ops);

-- =====================
-- ENUM FOR POST TARGETS
-- =====================
DO $$
BEGIN
    CREATE TYPE post_target AS ENUM ('twitter', 'linkedin', 'journal', 'resume');
EXCEPTION WHEN duplicate_object THEN NULL;
END$$;

-- =====================
-- USER POSTS
-- =====================
CREATE TABLE IF NOT EXISTS "user_post" (
    "post_id"      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "userId"       TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"      BIGINT REFERENCES "repository"("repo_id"),
    "event_ids"    UUID[] NOT NULL,
    "content_md"   TEXT NOT NULL,
    "target"       post_target NOT NULL,
    "status"       TEXT CHECK ("status" IN ('draft','published','archived')) DEFAULT 'draft',
    "context_hash" UUID,
    "createdAt"    TIMESTAMPTZ DEFAULT NOW(),
    "published_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_user_post_target ON "user_post"("userId", "target", "createdAt" DESC);

-- =====================
-- RESUME BULLETS
-- =====================
CREATE TABLE IF NOT EXISTS "resume_bullet" (
    "bullet_id"    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "userId"       TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"      BIGINT REFERENCES "repository"("repo_id"),
    "event_ids"    UUID[] NOT NULL,
    "bullet_latex" TEXT NOT NULL,
    "keywords"     TEXT[],
    "createdAt"    TIMESTAMPTZ DEFAULT NOW()
);

-- =====================
-- POST TEMPLATES
-- =====================
CREATE TABLE IF NOT EXISTS "post_template" (
    "template_id"   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "userId"        TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "target"        post_target NOT NULL,
    "template_name" TEXT NOT NULL,
    "prompt"        TEXT NOT NULL,
    "is_default"    BOOLEAN DEFAULT FALSE,
    "createdAt"     TIMESTAMPTZ DEFAULT NOW()
);

-- =====================
-- CONTEXT STATE
-- =====================
CREATE TABLE IF NOT EXISTS "post_context" (
    "context_id"     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "userId"         TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"        BIGINT REFERENCES "repository"("repo_id"),
    "target"         post_target NOT NULL,
    "last_event_at"  TIMESTAMPTZ,
    "last_post_id"   UUID REFERENCES "user_post"("post_id"),
    UNIQUE ("userId", "repo_id", "target")
);

-- =====================
-- WEBHOOKS
-- =====================
CREATE TABLE IF NOT EXISTS "repo_webhook" (
    "webhook_id"       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "userId"           TEXT REFERENCES "user"("id") ON DELETE CASCADE,
    "repo_id"          BIGINT REFERENCES "repository"("repo_id") ON DELETE CASCADE,
    "github_webhook_id" BIGINT UNIQUE NOT NULL,
    "url"              TEXT NOT NULL,
    "secret"           TEXT NOT NULL,
    "events"           TEXT[] NOT NULL,
    "is_active"        BOOLEAN NOT NULL DEFAULT TRUE,
    "createdAt"        TIMESTAMPTZ DEFAULT NOW(),
    "updatedAt"        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_repo_webhook_user ON "repo_webhook"("userId");
CREATE INDEX IF NOT EXISTS idx_repo_webhook_repo ON "repo_webhook"("repo_id");

-- =====================
-- UpdatedAt Auto Update Trigger
-- =====================
CREATE OR REPLACE FUNCTION update_updatedAt_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW."updatedAt" = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_updatedAt BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();
CREATE TRIGGER trg_repository_updatedAt BEFORE UPDATE ON "repository" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();
CREATE TRIGGER trg_account_updatedAt BEFORE UPDATE ON "account" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();
CREATE TRIGGER trg_session_updatedAt BEFORE UPDATE ON "session" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();
CREATE TRIGGER trg_verification_updatedAt BEFORE UPDATE ON "verification" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();
CREATE TRIGGER trg_repo_webhook_updatedAt BEFORE UPDATE ON "repo_webhook" FOR EACH ROW EXECUTE FUNCTION update_updatedAt_column();


CREATE OR REPLACE FUNCTION recalc_user_polling_state(p_user_id TEXT)
RETURNS VOID AS $$
DECLARE
    last_seen TIMESTAMPTZ;
    new_priority SMALLINT;
    new_interval INTERVAL;
BEGIN
    SELECT MAX("updatedAt") INTO last_seen
    FROM "session"
    WHERE "userId" = p_user_id;

    IF last_seen IS NULL THEN
        new_priority := 3;
        new_interval := interval '12 hours';
    ELSE
        IF last_seen >= NOW() - interval '12 hours' THEN
            new_priority := 1;
            new_interval := interval '10 seconds';    
        ELSIF last_seen >= NOW() - interval '72 hours' THEN
            new_priority := 2;
            new_interval := interval '6 hours';       
        ELSE
            new_priority := 3;
            new_interval := interval '12 hours';      
        END IF;
    END IF;

    INSERT INTO "user_polling_state"
        ("userId", "polling_interval", "next_scheduled_at", "priority", "source", "updatedAt")
    VALUES
        (p_user_id, new_interval, NOW() + new_interval, new_priority, 'login', NOW())
    ON CONFLICT ("userId") DO UPDATE
    SET
        "polling_interval" = EXCLUDED."polling_interval",
        "next_scheduled_at" = NOW() + EXCLUDED."polling_interval",
        "priority" = EXCLUDED."priority",
        "source" = EXCLUDED."source",
        "updatedAt" = NOW();
END;
$$ LANGUAGE plpgsql;


-- =====================
-- Trigger: On session insert/update -> Recalc polling
-- =====================
CREATE OR REPLACE FUNCTION trg_update_polling_on_session()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM recalc_user_polling_state(NEW."userId");
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_session_update_polling ON "session";
CREATE TRIGGER after_session_update_polling
AFTER INSERT OR UPDATE ON "session"
FOR EACH ROW
EXECUTE FUNCTION trg_update_polling_on_session();

-- =====================
-- Trigger: On event insert -> update polling fetch time
-- =====================
CREATE OR REPLACE FUNCTION trg_update_polling_on_event_fetch()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE "user_polling_state"
    SET "last_event_fetch" = NOW(),
        "last_event_id_gh" = GREATEST(COALESCE("last_event_id_gh", 0), NEW."event_id_gh"),
        "next_scheduled_at" = NOW() + "polling_interval",
        "source" = COALESCE(NEW."source", 'cron'),
        "updatedAt" = NOW()
    WHERE "userId" = NEW."userId";
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_event_insert_polling ON "github_event";
CREATE TRIGGER after_event_insert_polling
AFTER INSERT ON "github_event"
FOR EACH ROW
EXECUTE FUNCTION trg_update_polling_on_event_fetch();
