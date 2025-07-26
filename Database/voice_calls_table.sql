-- Create voice_calls table for tracking voice call data
CREATE TABLE IF NOT EXISTS voice_calls (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    call_id VARCHAR(255) NOT NULL UNIQUE,
    agent_id VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    gem_cost INTEGER NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'initiated',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key to users table
    CONSTRAINT fk_voice_calls_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(telegram_id) 
        ON DELETE CASCADE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_voice_calls_user_id ON voice_calls(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_call_id ON voice_calls(call_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_created_at ON voice_calls(created_at);

-- Add RLS (Row Level Security) policies
ALTER TABLE voice_calls ENABLE ROW LEVEL SECURITY;

-- Policy to allow users to see only their own calls (if needed for user dashboard)
CREATE POLICY "Users can view their own voice calls" ON voice_calls
    FOR SELECT USING (auth.uid()::bigint = user_id);

-- Policy to allow service role to insert/update calls
CREATE POLICY "Service role can manage voice calls" ON voice_calls
    FOR ALL USING (auth.role() = 'service_role');

-- Add comments for documentation
COMMENT ON TABLE voice_calls IS 'Tracks voice calls made through ElevenLabs/Twilio integration';
COMMENT ON COLUMN voice_calls.user_id IS 'Telegram user ID who made the call';
COMMENT ON COLUMN voice_calls.call_id IS 'Unique call identifier from ElevenLabs/Twilio';
COMMENT ON COLUMN voice_calls.agent_id IS 'ElevenLabs agent ID used for the call';
COMMENT ON COLUMN voice_calls.phone_number IS 'Phone number that received the call';
COMMENT ON COLUMN voice_calls.gem_cost IS 'Gems charged for this call';
COMMENT ON COLUMN voice_calls.duration_minutes IS 'Call duration in minutes (updated after call ends)';
COMMENT ON COLUMN voice_calls.status IS 'Call status: initiated, completed, failed'; 