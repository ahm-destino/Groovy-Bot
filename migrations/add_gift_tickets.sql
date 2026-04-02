-- Migration: Add gift tickets support
-- Allows users to purchase tickets as gifts and send to recipients

-- Add gift fields to bookings table
ALTER TABLE bookings 
ADD COLUMN IF NOT EXISTS is_gift BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gift_sender_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS gift_recipient_phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS gift_message TEXT,
ADD COLUMN IF NOT EXISTS gift_redeemed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gift_redeemed_at TIMESTAMP WITH TIME ZONE;

-- Add gift fields to tickets table
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS is_gift BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gift_from_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS gift_message TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bookings_is_gift ON bookings(is_gift);
CREATE INDEX IF NOT EXISTS idx_bookings_gift_sender ON bookings(gift_sender_id);
CREATE INDEX IF NOT EXISTS idx_bookings_gift_recipient ON bookings(gift_recipient_phone);
CREATE INDEX IF NOT EXISTS idx_tickets_is_gift ON tickets(is_gift);

-- Add comments
COMMENT ON COLUMN bookings.is_gift IS 'Whether this booking is a gift purchase';
COMMENT ON COLUMN bookings.gift_sender_id IS 'User who purchased the gift';
COMMENT ON COLUMN bookings.gift_recipient_phone IS 'Phone number of gift recipient';
COMMENT ON COLUMN bookings.gift_message IS 'Personal message from sender';
COMMENT ON COLUMN bookings.gift_redeemed IS 'Whether recipient has received the gift';
COMMENT ON COLUMN tickets.is_gift IS 'Whether this ticket was received as a gift';
COMMENT ON COLUMN tickets.gift_from_name IS 'Name of person who sent the gift';
