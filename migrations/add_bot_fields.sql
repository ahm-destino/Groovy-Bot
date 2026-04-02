-- Migration: Add WhatsApp Bot Fields to Existing Grooovy Database
-- Run this on your existing Supabase database to enable bot integration

-- ============================================================================
-- USERS TABLE - Add WhatsApp fields
-- ============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS location_preference GEOGRAPHY(POINT, 4326);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_categories TEXT[];
ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

COMMENT ON COLUMN users.phone IS 'WhatsApp phone number (E.164 format)';
COMMENT ON COLUMN users.whatsapp_name IS 'Name from WhatsApp profile';
COMMENT ON COLUMN users.location_preference IS 'Default location for event discovery';
COMMENT ON COLUMN users.preferred_categories IS 'Array of preferred event categories';

-- ============================================================================
-- EVENTS TABLE - Add anonymous event fields
-- ============================================================================

ALTER TABLE events ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS anonymous_mode VARCHAR(20);
ALTER TABLE events ADD COLUMN IF NOT EXISTS secret_code VARCHAR(50) UNIQUE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS location_reveal_trigger VARCHAR(20);
ALTER TABLE events ADD COLUMN IF NOT EXISTS location_reveal_hours_before INTEGER;
ALTER TABLE events ADD COLUMN IF NOT EXISTS entry_code_format VARCHAR(20);
ALTER TABLE events ADD COLUMN IF NOT EXISTS shared_entry_code VARCHAR(50);
ALTER TABLE events ADD COLUMN IF NOT EXISTS location_revealed BOOLEAN DEFAULT FALSE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS location_revealed_at TIMESTAMPTZ;
ALTER TABLE events ADD COLUMN IF NOT EXISTS created_via VARCHAR(20) DEFAULT 'webapp';

COMMENT ON COLUMN events.is_anonymous IS 'Whether event has privacy features enabled';
COMMENT ON COLUMN events.anonymous_mode IS 'Type: code_required, location_hidden, hybrid';
COMMENT ON COLUMN events.secret_code IS 'Code required to discover event';
COMMENT ON COLUMN events.location_reveal_trigger IS 'When to reveal: immediate, time_based, manual';
COMMENT ON COLUMN events.location_reveal_hours_before IS 'Hours before event to reveal location';
COMMENT ON COLUMN events.entry_code_format IS 'Entry code type: shared, unique_per_ticket';
COMMENT ON COLUMN events.shared_entry_code IS 'Single code for all attendees';
COMMENT ON COLUMN events.created_via IS 'Source: webapp, whatsapp';

-- ============================================================================
-- BOOKINGS TABLE - Add payment and tracking fields
-- ============================================================================

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100) UNIQUE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booked_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_source VARCHAR(20) DEFAULT 'webapp';

COMMENT ON COLUMN bookings.phone IS 'Phone number used for booking (WhatsApp)';
COMMENT ON COLUMN bookings.payment_reference IS 'Paystack transaction reference';
COMMENT ON COLUMN bookings.payment_method IS 'Payment method: card, bank, ussd, mobile_money';
COMMENT ON COLUMN bookings.booking_source IS 'Source: webapp, whatsapp';

-- ============================================================================
-- TICKETS TABLE - Add anonymous event fields
-- ============================================================================

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS entry_code VARCHAR(50);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed BOOLEAN DEFAULT FALSE;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed_at TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ;

COMMENT ON COLUMN tickets.entry_code IS 'Code for venue entry (anonymous events)';
COMMENT ON COLUMN tickets.location_revealed IS 'Whether location has been revealed to ticket holder';
COMMENT ON COLUMN tickets.checked_in_at IS 'Timestamp of venue check-in';

-- ============================================================================
-- NEW TABLES - Bot-specific tables
-- ============================================================================

-- Conversation state tracking
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    phone VARCHAR(20) NOT NULL,
    current_flow VARCHAR(50),
    flow_state JSONB,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE conversations IS 'WhatsApp conversation state for multi-turn flows';
COMMENT ON COLUMN conversations.current_flow IS 'Active flow: event_creation, booking, etc.';
COMMENT ON COLUMN conversations.flow_state IS 'JSON state data for current flow';

-- Message logs for analytics and debugging
CREATE TABLE IF NOT EXISTS message_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) NOT NULL,
    direction VARCHAR(10),
    message_type VARCHAR(20),
    content TEXT,
    whatsapp_message_id VARCHAR(255),
    intent_detected VARCHAR(50),
    entities JSONB,
    response_time_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE message_logs IS 'Log of all WhatsApp messages for analytics';
COMMENT ON COLUMN message_logs.direction IS 'inbound or outbound';
COMMENT ON COLUMN message_logs.intent_detected IS 'AI-detected intent';
COMMENT ON COLUMN message_logs.entities IS 'Extracted entities (location, date, etc.)';

-- Anonymous event access logs
CREATE TABLE IF NOT EXISTS anonymous_access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id),
    user_id UUID REFERENCES users(id),
    phone VARCHAR(20),
    code_used VARCHAR(50),
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

COMMENT ON TABLE anonymous_access_logs IS 'Track secret code usage for anonymous events';

-- ============================================================================
-- INDEXES - Performance optimization
-- ============================================================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- Events
CREATE INDEX IF NOT EXISTS idx_events_secret_code ON events(secret_code);
CREATE INDEX IF NOT EXISTS idx_events_anonymous ON events(is_anonymous, status);
CREATE INDEX IF NOT EXISTS idx_events_created_via ON events(created_via);

-- Bookings
CREATE INDEX IF NOT EXISTS idx_bookings_payment_ref ON bookings(payment_reference);
CREATE INDEX IF NOT EXISTS idx_bookings_phone ON bookings(phone);
CREATE INDEX IF NOT EXISTS idx_bookings_source ON bookings(booking_source);

-- Conversations
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- Message Logs
CREATE INDEX IF NOT EXISTS idx_message_logs_phone ON message_logs(phone);
CREATE INDEX IF NOT EXISTS idx_message_logs_created ON message_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_message_logs_intent ON message_logs(intent_detected);

-- Anonymous Access Logs
CREATE INDEX IF NOT EXISTS idx_anonymous_logs_event ON anonymous_access_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_anonymous_logs_phone ON anonymous_access_logs(phone);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Optional but recommended
-- ============================================================================

-- Enable RLS on new tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE anonymous_access_logs ENABLE ROW LEVEL SECURITY;

-- Conversations: Users can only see their own
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id OR phone = (SELECT phone FROM users WHERE id = auth.uid()));

-- Message logs: Users can only see their own
CREATE POLICY "Users can view own messages" ON message_logs
  FOR SELECT USING (phone = (SELECT phone FROM users WHERE id = auth.uid()));

-- Anonymous access logs: Users can see their own unlocks
CREATE POLICY "Users can view own access logs" ON anonymous_access_logs
  FOR SELECT USING (auth.uid() = user_id OR phone = (SELECT phone FROM users WHERE id = auth.uid()));

-- Note: Bot uses service_role key which bypasses RLS

-- ============================================================================
-- FUNCTIONS - Helper functions for webapp
-- ============================================================================

-- Function to get user's WhatsApp bookings
CREATE OR REPLACE FUNCTION get_user_whatsapp_bookings(user_uuid UUID)
RETURNS TABLE (
    booking_id UUID,
    event_title VARCHAR,
    event_date TIMESTAMPTZ,
    quantity INTEGER,
    total_amount DECIMAL,
    status VARCHAR,
    booking_source VARCHAR,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        b.id,
        e.title,
        e.event_date,
        b.quantity,
        b.total_amount,
        b.status,
        b.booking_source,
        b.created_at
    FROM bookings b
    JOIN events e ON e.id = b.event_id
    WHERE b.user_id = user_uuid
    ORDER BY b.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to check if phone number is already registered
CREATE OR REPLACE FUNCTION is_phone_registered(phone_number VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1 FROM users WHERE phone = phone_number);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS - Useful views for analytics
-- ============================================================================

-- View: Bookings by source
CREATE OR REPLACE VIEW bookings_by_source AS
SELECT 
    booking_source,
    COUNT(*) as total_bookings,
    SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_bookings,
    SUM(CASE WHEN status = 'confirmed' THEN total_amount ELSE 0 END) as total_revenue
FROM bookings
GROUP BY booking_source;

-- View: Events by creation method
CREATE OR REPLACE VIEW events_by_source AS
SELECT 
    created_via,
    COUNT(*) as total_events,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_events,
    SUM(tickets_sold) as total_tickets_sold
FROM events
GROUP BY created_via;

-- View: WhatsApp bot usage stats
CREATE OR REPLACE VIEW whatsapp_bot_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(DISTINCT phone) as unique_users,
    COUNT(*) as total_messages,
    COUNT(CASE WHEN direction = 'inbound' THEN 1 END) as inbound_messages,
    COUNT(CASE WHEN direction = 'outbound' THEN 1 END) as outbound_messages,
    AVG(response_time_ms) as avg_response_time_ms
FROM message_logs
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ============================================================================
-- TRIGGERS - Automatic updates
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to users table if not already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_users_updated_at'
    ) THEN
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Apply to events table if not already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_events_updated_at'
    ) THEN
        CREATE TRIGGER update_events_updated_at
        BEFORE UPDATE ON events
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ============================================================================
-- GRANTS - Permissions for service role
-- ============================================================================

-- Grant bot service role full access to all tables
-- (Supabase service_role already has full access, but explicit for clarity)

GRANT ALL ON users TO service_role;
GRANT ALL ON events TO service_role;
GRANT ALL ON bookings TO service_role;
GRANT ALL ON tickets TO service_role;
GRANT ALL ON conversations TO service_role;
GRANT ALL ON message_logs TO service_role;
GRANT ALL ON anonymous_access_logs TO service_role;

-- ============================================================================
-- VERIFICATION - Check migration success
-- ============================================================================

-- Verify new columns exist
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'phone') = 1,
           'users.phone column not created';
    
    ASSERT (SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'events' AND column_name = 'is_anonymous') = 1,
           'events.is_anonymous column not created';
    
    ASSERT (SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'bookings' AND column_name = 'booking_source') = 1,
           'bookings.booking_source column not created';
    
    ASSERT (SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'conversations') = 1,
           'conversations table not created';
    
    RAISE NOTICE 'Migration completed successfully!';
END $$;

-- ============================================================================
-- DONE!
-- ============================================================================

-- Migration complete. The database is now ready for WhatsApp bot integration.
-- Next steps:
-- 1. Update bot .env with DATABASE_URL
-- 2. Deploy bot
-- 3. Test integration
