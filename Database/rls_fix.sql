-- ===============================================
-- FIX RLS POLICIES FOR BOT SERVICE ROLE ACCESS
-- ===============================================

-- Drop the restrictive policies and create new ones that work with service role key
DROP POLICY IF EXISTS "Service role can manage conversations" ON public.conversations;
CREATE POLICY "Service role can manage conversations" ON public.conversations
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role');

DROP POLICY IF EXISTS "Service role can manage subscriptions" ON public.subscriptions;
CREATE POLICY "Service role can manage subscriptions" ON public.subscriptions
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role');

DROP POLICY IF EXISTS "Service role can manage users" ON public.users;
CREATE POLICY "Service role can manage users" ON public.users
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role');

DROP POLICY IF EXISTS "Service role can manage payments" ON public.processed_payments;
CREATE POLICY "Service role can manage payments" ON public.processed_payments
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role');

DROP POLICY IF EXISTS "Service role can manage star earnings" ON public.star_earnings;
CREATE POLICY "Service role can manage star earnings" ON public.star_earnings
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role');

DROP POLICY IF EXISTS "Service role can manage voice calls" ON public.voice_calls;
CREATE POLICY "Service role can manage voice calls" ON public.voice_calls
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'service_role' OR current_setting('role') = 'service_role'); 