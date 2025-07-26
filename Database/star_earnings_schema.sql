-- =================================================================
-- STAR EARNINGS TRACKING EXTENSION - Secret Share Bot
-- Add this to your existing Supabase database for revenue analytics
-- =================================================================

-- Create earnings tracking table
CREATE TABLE IF NOT EXISTS public.star_earnings (
    id BIGSERIAL PRIMARY KEY,
    telegram_charge_id VARCHAR(255) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    payload VARCHAR(100) NOT NULL,
    stars_amount INTEGER NOT NULL,
    payment_type VARCHAR(50) NOT NULL, -- 'gems' or 'subscription'
    gems_granted INTEGER DEFAULT 0,
    subscription_tier VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_star_earnings_created_at ON public.star_earnings(created_at);
CREATE INDEX IF NOT EXISTS idx_star_earnings_user_id ON public.star_earnings(user_id);
CREATE INDEX IF NOT EXISTS idx_star_earnings_payment_type ON public.star_earnings(payment_type);

-- Create analytics view for easy querying
CREATE OR REPLACE VIEW public.earnings_analytics AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_transactions,
    SUM(stars_amount) as stars_earned,
    SUM(CASE WHEN payment_type = 'gems' THEN stars_amount ELSE 0 END) as gems_revenue,
    SUM(CASE WHEN payment_type = 'subscription' THEN stars_amount ELSE 0 END) as subscription_revenue,
    COUNT(DISTINCT user_id) as unique_customers
FROM public.star_earnings
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Create monthly summary view
CREATE OR REPLACE VIEW public.monthly_earnings AS
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as total_transactions,
    SUM(stars_amount) as total_stars,
    COUNT(DISTINCT user_id) as unique_customers,
    AVG(stars_amount) as avg_transaction_value
FROM public.star_earnings
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- Create top customers view
CREATE OR REPLACE VIEW public.top_customers AS
SELECT 
    u.telegram_id,
    u.username,
    u.user_name,
    COUNT(se.id) as total_purchases,
    SUM(se.stars_amount) as total_stars_spent,
    MAX(se.created_at) as last_purchase_date
FROM public.users u
JOIN public.star_earnings se ON u.telegram_id = se.user_id
GROUP BY u.telegram_id, u.username, u.user_name
ORDER BY total_stars_spent DESC;

-- Function to get total earnings
CREATE OR REPLACE FUNCTION get_total_earnings()
RETURNS TABLE(
    total_stars BIGINT,
    total_transactions BIGINT,
    total_customers BIGINT,
    gems_revenue BIGINT,
    subscription_revenue BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(stars_amount), 0)::BIGINT as total_stars,
        COUNT(*)::BIGINT as total_transactions,
        COUNT(DISTINCT user_id)::BIGINT as total_customers,
        COALESCE(SUM(CASE WHEN payment_type = 'gems' THEN stars_amount ELSE 0 END), 0)::BIGINT as gems_revenue,
        COALESCE(SUM(CASE WHEN payment_type = 'subscription' THEN stars_amount ELSE 0 END), 0)::BIGINT as subscription_revenue
    FROM public.star_earnings;
END;
$$ LANGUAGE plpgsql;

-- Function to get earnings for a specific period
CREATE OR REPLACE FUNCTION get_earnings_period(period_days INTEGER DEFAULT 30)
RETURNS TABLE(
    total_stars BIGINT,
    total_transactions BIGINT,
    unique_customers BIGINT,
    avg_transaction_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(stars_amount), 0)::BIGINT as total_stars,
        COUNT(*)::BIGINT as total_transactions,
        COUNT(DISTINCT user_id)::BIGINT as unique_customers,
        COALESCE(AVG(stars_amount), 0)::NUMERIC as avg_transaction_value
    FROM public.star_earnings
    WHERE created_at >= NOW() - INTERVAL '%s days', period_days::TEXT;
END;
$$ LANGUAGE plpgsql; 