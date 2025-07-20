CREATE TABLE IF NOT EXISTS public.repositories (
    id               BIGINT PRIMARY KEY,
    node_id          TEXT UNIQUE,
    name             TEXT NOT NULL,
    full_name        TEXT UNIQUE NOT NULL,
    owner_login      TEXT NOT NULL,
    owner_type       TEXT CHECK (owner_type IN ('user','organisation')),
    private          BOOLEAN,
    default_branch   TEXT,
    description      TEXT,
    language         TEXT,
    topics           TEXT[],
    homepage         TEXT,
    license          JSONB,
    stargazers_count INT,
    forks_count      INT,
    created_at_gh    TIMESTAMPTZ,
    updated_at_gh    TIMESTAMPTZ,
    pushed_at_gh     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_repository (
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories ON DELETE CASCADE,
    relationship  TEXT CHECK (relationship IN ('owner','collaborator','contributor')),
    PRIMARY KEY (user_id, repo_id)
);

CREATE TABLE IF NOT EXISTS public.github_events (
    id            UUID DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories ON DELETE CASCADE,
    event_type    TEXT,
    event_id_gh   BIGINT,
    payload       JSONB NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    processed     BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, occurred_at)  
);

SELECT create_hypertable('public.github_events', 'occurred_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_github_events_user_occurred_at
    ON public.github_events (user_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_github_events_repo_occurred_at
    ON public.github_events (repo_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS public.code_changes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id      UUID NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    sha           TEXT,
    patch         TEXT,
    files_changed JSONB,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_id, occurred_at)
      REFERENCES public.github_events (id, occurred_at)
      ON DELETE CASCADE
);