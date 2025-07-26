-- =================================================================
-- Secret Share Bot: Production Supabase Schema v4 (Voice Integration)
-- This script is idempotent and robust. It can be run safely
-- on a new database or an existing one to ensure all required
-- columns, tables, and functions are present.
-- =================================================================

-- Step 1: Create the 'users' table if it doesn't exist.
CREATE TABLE IF NOT EXISTS public.users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    gems INTEGER DEFAULT 100
);

-- Step 2: Add all required columns to the 'users' table if they don't exist.
-- This is the crucial step for updating an existing table.
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS user_name TEXT,
ADD COLUMN IF NOT EXISTS messages_today INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_message_date TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS total_messages INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS age_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS subscription_type TEXT,
ADD COLUMN IF NOT EXISTS subscription_end TIMESTAMPTZ,
-- THIS IS THE FIX: Explicitly add the missing column for the retention engine.
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ DEFAULT NOW();

-- Step 3: Create the 'conversations' table if it doesn't exist.
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id BIGINT NOT NULL, -- This is the user's telegram_id
    character TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 4: Create the 'voice_calls' table for tracking voice calls
CREATE TABLE IF NOT EXISTS public.voice_calls (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    call_id VARCHAR(255) NOT NULL UNIQUE,
    agent_id VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    gem_cost INTEGER NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'initiated',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Foreign key to users table
    CONSTRAINT fk_voice_calls_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(telegram_id) 
        ON DELETE CASCADE
);

-- Step 5: Create or Replace the message incrementing function.
-- This function is now safe because we've guaranteed the 'last_seen' column exists.
CREATE OR REPLACE FUNCTION public.increment_user_messages(p_user_id BIGINT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.users
  SET
    messages_today = messages_today + 1,
    total_messages = total_messages + 1,
    last_message_date = NOW(),
    last_seen = NOW() -- This will now work correctly.
  WHERE
    telegram_id = p_user_id;
END;
$$;

-- Step 6: Create function to log voice calls
CREATE OR REPLACE FUNCTION public.log_voice_call(
    p_user_id BIGINT,
    p_call_id VARCHAR(255),
    p_agent_id VARCHAR(255),
    p_phone_number VARCHAR(20),
    p_gem_cost INTEGER DEFAULT 0
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public.voice_calls (
    user_id,
    call_id,
    agent_id,
    phone_number,
    gem_cost,
    status,
    created_at
  ) VALUES (
    p_user_id,
    p_call_id,
    p_agent_id,
    p_phone_number,
    p_gem_cost,
    'initiated',
    NOW()
  );
END;
$$;

-- Step 7: Create function to update call duration
CREATE OR REPLACE FUNCTION public.update_call_duration(
    p_call_id VARCHAR(255),
    p_duration_minutes INTEGER
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.voice_calls
  SET
    duration_minutes = p_duration_minutes,
    status = 'completed',
    updated_at = NOW()
  WHERE
    call_id = p_call_id;
END;
$$;

-- Step 8: Create all necessary indexes for performance if they don't exist.
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON public.users(last_seen);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_user_id ON public.voice_calls(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_call_id ON public.voice_calls(call_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_created_at ON public.voice_calls(created_at);

-- Step 9: Add RLS (Row Level Security) policies for voice_calls table
ALTER TABLE public.voice_calls ENABLE ROW LEVEL SECURITY;

-- Policy to allow service role to manage voice calls (for bot operations)
DROP POLICY IF EXISTS "Service role can manage voice calls" ON public.voice_calls;
CREATE POLICY "Service role can manage voice calls" ON public.voice_calls
    FOR ALL USING (auth.role() = 'service_role');

-- Note: No additional user-based policies needed since the bot uses service role authentication

-- Step 10: Add comments for documentation
COMMENT ON TABLE public.voice_calls IS 'Tracks voice calls made through ElevenLabs/Twilio integration';
COMMENT ON COLUMN public.voice_calls.user_id IS 'Telegram user ID who made the call';
COMMENT ON COLUMN public.voice_calls.call_id IS 'Unique call identifier from ElevenLabs/Twilio';
COMMENT ON COLUMN public.voice_calls.agent_id IS 'ElevenLabs agent ID used for the call';
COMMENT ON COLUMN public.voice_calls.phone_number IS 'Phone number that received the call';
COMMENT ON COLUMN public.voice_calls.gem_cost IS 'Gems charged for this call';
COMMENT ON COLUMN public.voice_calls.duration_minutes IS 'Call duration in minutes (updated after call ends)';
COMMENT ON COLUMN public.voice_calls.status IS 'Call status: initiated, completed, failed';

-- Step 11: Create a view for call analytics (optional)
CREATE OR REPLACE VIEW public.voice_call_analytics AS
SELECT 
    u.telegram_id,
    u.username,
    u.user_name,
    COUNT(vc.id) as total_calls,
    SUM(vc.duration_minutes) as total_duration_minutes,
    SUM(vc.gem_cost) as total_gems_spent,
    AVG(vc.duration_minutes) as avg_call_duration,
    MAX(vc.created_at) as last_call_date
FROM public.users u
LEFT JOIN public.voice_calls vc ON u.telegram_id = vc.user_id
GROUP BY u.telegram_id, u.username, u.user_name;

-- Final confirmation message.
SELECT 'Supabase schema v4 setup complete. All tables, columns, functions, and voice call tracking are now correctly configured.' AS status; 