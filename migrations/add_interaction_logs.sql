-- Add interaction_logs table for button/list analytics
CREATE TABLE IF NOT EXISTS interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    kind VARCHAR(20),
    context VARCHAR(100),
    options JSONB,
    selected_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    selected_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_interaction_logs_phone ON interaction_logs(phone);
CREATE INDEX IF NOT EXISTS idx_interaction_logs_created_at ON interaction_logs(created_at);
