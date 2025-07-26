-- Fix RLS policies for Secret Share Bot
-- Run this in Supabase SQL Editor

-- Disable RLS temporarily to fix policies
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_payments DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.star_earnings DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.voice_calls DISABLE ROW LEVEL SECURITY;

-- Re-enable RLS with correct policies
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.star_earnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.voice_calls ENABLE ROW LEVEL SECURITY;

-- Create permissive policies for service role
DROP POLICY IF EXISTS "Service role full access" ON public.users;
CREATE POLICY "Service role full access" ON public.users
    FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role payments access" ON public.processed_payments;
CREATE POLICY "Service role payments access" ON public.processed_payments
    FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role earnings access" ON public.star_earnings;
CREATE POLICY "Service role earnings access" ON public.star_earnings
    FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role calls access" ON public.voice_calls;
CREATE POLICY "Service role calls access" ON public.voice_calls
    FOR ALL USING (true);

-- Grant necessary permissions
GRANT ALL ON public.users TO authenticated;
GRANT ALL ON public.users TO service_role;
GRANT ALL ON public.processed_payments TO authenticated;
GRANT ALL ON public.processed_payments TO service_role;
GRANT ALL ON public.star_earnings TO authenticated;
GRANT ALL ON public.star_earnings TO service_role;
GRANT ALL ON public.voice_calls TO authenticated;
GRANT ALL ON public.voice_calls TO service_role;

SELECT 'RLS policies fixed! Bot should work now.' AS status;
