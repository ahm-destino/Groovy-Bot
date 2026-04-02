-- Migration: Add promo codes support
-- This allows organizers to create discount codes for events

-- Create promo_codes table
CREATE TABLE IF NOT EXISTS promo_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL, -- percentage, fixed_amount
    discount_value DECIMAL(10, 2) NOT NULL,
    max_uses INTEGER, -- NULL = unlimited
    current_uses INTEGER DEFAULT 0,
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    min_tickets INTEGER DEFAULT 1, -- Minimum tickets required
    max_discount_amount DECIMAL(10, 2), -- Cap for percentage discounts
    status VARCHAR(20) DEFAULT 'active', -- active, expired, disabled
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT discount_value_check CHECK (discount_value > 0),
    CONSTRAINT max_uses_check CHECK (max_uses IS NULL OR max_uses > 0),
    CONSTRAINT current_uses_check CHECK (current_uses >= 0)
);

-- Add promo_code_id to bookings table
ALTER TABLE bookings 
ADD COLUMN IF NOT EXISTS promo_code_id UUID REFERENCES promo_codes(id),
ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10, 2) DEFAULT 0;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_promo_codes_event_id ON promo_codes(event_id);
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_status ON promo_codes(status);
CREATE INDEX IF NOT EXISTS idx_bookings_promo_code_id ON bookings(promo_code_id);

-- Add comments
COMMENT ON TABLE promo_codes IS 'Discount codes for events';
COMMENT ON COLUMN promo_codes.discount_type IS 'percentage (e.g., 20 for 20%) or fixed_amount (e.g., 5000 for ₦5000 off)';
COMMENT ON COLUMN promo_codes.max_uses IS 'Maximum number of times code can be used (NULL = unlimited)';
COMMENT ON COLUMN promo_codes.max_discount_amount IS 'Maximum discount for percentage codes';
