CREATE TABLE IF NOT EXISTS public.context_state (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories,
    target        public.post_target NOT NULL,
    last_event_at TIMESTAMPTZ,
    last_post_id  UUID REFERENCES public.posts,
    UNIQUE (user_id, repo_id, target)
);