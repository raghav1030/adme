CREATE TABLE IF NOT EXISTS public.summaries (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id      UUID NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    summary_text  TEXT NOT NULL,
    tech_stack    TEXT[],
    embedding     VECTOR(1536),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_id, occurred_at)
        REFERENCES public.github_events (id, occurred_at)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_summaries_embedding
    ON public.summaries USING diskann (embedding);

DO $$
BEGIN
    CREATE TYPE public.post_target AS ENUM ('twitter', 'linkedin', 'journal', 'resume');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END$$;

CREATE TABLE IF NOT EXISTS public.posts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories,
    event_ids     UUID[] NOT NULL,
    content_md    TEXT NOT NULL,
    target        public.post_target NOT NULL,
    status        TEXT CHECK (status IN ('draft', 'published', 'archived')) DEFAULT 'draft',
    context_hash  UUID,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    published_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_posts_user_target_created_at
    ON public.posts (user_id, target, created_at DESC);

CREATE TABLE IF NOT EXISTS public.resume_bullets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories,
    event_ids     UUID[] NOT NULL,
    bullet_latex  TEXT NOT NULL,
    keywords      TEXT[],
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.post_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    target        public.post_target NOT NULL,
    name          TEXT,
    prompt        TEXT NOT NULL,
    is_default    BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_github_events_id_occurred
    ON public.github_events (id, occurred_at); 