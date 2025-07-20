
CREATE TABLE IF NOT EXISTS public.users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    full_name     TEXT,
    avatar_url    TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS public.oauth_providers (
    provider      TEXT PRIMARY KEY,
    issuer_url    TEXT
);


CREATE TABLE IF NOT EXISTS public.user_oauth (
    user_id       UUID REFERENCES public.users ON DELETE CASCADE,
    provider      TEXT REFERENCES public.oauth_providers,
    provider_uid  TEXT,
    access_token  TEXT,          
    refresh_token TEXT,          
    scope         TEXT[],
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, provider)
);


CREATE TABLE IF NOT EXISTS public.organisations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    domain        TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_organisation (
    user_id         UUID REFERENCES public.users ON DELETE CASCADE,
    organisation_id UUID REFERENCES public.organisations ON DELETE CASCADE,
    role            TEXT CHECK (role IN ('owner','member')),
    PRIMARY KEY (user_id, organisation_id)
);
