-- Migration: Add ticket tiers support
-- This allows events to have multiple ticket types (VIP, Regular, Early Bird, etc.)

-- Create ticket_tiers table
CREATE TABLE IF NOT EXISTS ticket_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- e.g., "VIP", "Regular", "Early Bird"
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    capacity INTEGER NOT NULL,
    tickets_sold INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0, -- Display order
    available_from TIMESTAMP WITH TIME ZONE, -- Optional: when tier becomes available
    available_until TIMESTAMP WITH TIME ZONE, -- Optional: when tier stops being available
    status VARCHAR(20) DEFAULT 'active', -- active, sold_out, disabled
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT tickets_sold_check CHECK (tickets_sold >= 0),
    CONSTRAINT capacity_check CHECK (capacity > 0),
    CONSTRAINT price_check CHECK (price >= 0)
);

-- Add tier_id to bookings table
ALTER TABLE bookings 
ADD COLUMN IF NOT EXISTS tier_id UUID REFERENCES ticket_tiers(id);

-- Add tier_id to tickets table
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS tier_id UUID REFERENCES ticket_tiers(id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ticket_tiers_event_id ON ticket_tiers(event_id);
CREATE INDEX IF NOT EXISTS idx_ticket_tiers_status ON ticket_tiers(status);
CREATE INDEX IF NOT EXISTS idx_bookings_tier_id ON bookings(tier_id);
CREATE INDEX IF NOT EXISTS idx_tickets_tier_id ON tickets(tier_id);

-- Add comments
COMMENT ON TABLE ticket_tiers IS 'Multiple ticket types per event (VIP, Regular, Early Bird, etc.)';
COMMENT ON COLUMN ticket_tiers.name IS 'Tier name displayed to users';
COMMENT ON COLUMN ticket_tiers.sort_order IS 'Display order (lower numbers first)';
COMMENT ON COLUMN ticket_tiers.available_from IS 'When this tier becomes available for purchase';
COMMENT ON COLUMN ticket_tiers.available_until IS 'When this tier stops being available';
