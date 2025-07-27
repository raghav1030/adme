CREATE TABLE public.webhooks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    repo_id       BIGINT REFERENCES public.repositories ON DELETE CASCADE,
    github_webhook_id BIGINT UNIQUE NOT NULL,
    url           TEXT NOT NULL,
    secret        TEXT NOT NULL,
    events        TEXT[] NOT NULL,
    active        BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON public.webhooks (user_id);
CREATE INDEX ON public.webhooks (repo_id);