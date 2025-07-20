CREATE SCHEMA IF NOT EXISTS auth;

CREATE OR REPLACE FUNCTION auth.uid()
RETURNS UUID
LANGUAGE plpgsql STABLE SECURITY DEFINER AS
$$
BEGIN
    -- Replace with whatever you put in jwt.claims.user_id
    RETURN current_setting('jwt.claims.user_id', TRUE)::UUID;
END;
$$;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.users
FOR ALL USING (auth.uid() = id);

ALTER TABLE public.user_oauth ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.user_oauth
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.user_repository ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.user_repository
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.github_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.github_events
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.code_changes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.code_changes
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM public.github_events e
        WHERE e.id = code_changes.event_id AND e.user_id = auth.uid()
    )
);

ALTER TABLE public.summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.summaries
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM public.github_events e
        WHERE e.id = summaries.event_id AND e.user_id = auth.uid()
    )
);

ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.posts
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.resume_bullets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.resume_bullets
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.post_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.post_templates
FOR ALL USING (user_id = auth.uid());

ALTER TABLE public.context_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own data only" ON public.context_state
FOR ALL USING (user_id = auth.uid());