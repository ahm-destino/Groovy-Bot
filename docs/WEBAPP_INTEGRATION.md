# Grooovy Webapp Integration Guide

## Overview

The WhatsApp bot shares the same Supabase database with the Grooovy webapp. This ensures:
- Users see their WhatsApp bookings in the webapp
- Organizers can manage bot-created events in the webapp
- Single source of truth for all data
- Seamless cross-platform experience

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPABASE DATABASE                        │
│                  (Shared PostgreSQL)                        │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
        ┌─────────▼─────────┐   ┌────────▼──────────┐
        │  Grooovy Webapp   │   │  WhatsApp Bot     │
        │  (Netlify)        │   │  (FastAPI)        │
        │                   │   │                   │
        │  - Web UI         │   │  - WhatsApp API   │
        │  - User accounts  │   │  - AI Engine      │
        │  - Event mgmt     │   │  - Payments       │
        └───────────────────┘   └───────────────────┘
```

## Database Connection

### Shared Supabase Project

Both the webapp and bot connect to the same Supabase project:

```env
# .env (Bot)
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Webapp (Supabase client)
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=[anon-key]
```

## Schema Compatibility

### Existing Webapp Tables

The bot extends the existing webapp schema with additional fields:

#### Users Table (Extended)
```sql
-- Existing webapp fields
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot additions (add these columns)
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS location_preference GEOGRAPHY(POINT, 4326);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_categories TEXT[];
ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

-- Index for bot lookups
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
```

#### Events Table (Extended)
```sql
-- Existing webapp fields
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    host_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    event_date TIMESTAMPTZ NOT NULL,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    full_address TEXT,
    venue_name VARCHAR(255),
    capacity INTEGER,
    tickets_sold INTEGER DEFAULT 0,
    ticket_price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'NGN',
    banner_image_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot additions for anonymous events
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_secret_code ON events(secret_code);
CREATE INDEX IF NOT EXISTS idx_events_anonymous ON events(is_anonymous, status);
```

#### Bookings Table (Extended)
```sql
-- Existing webapp fields
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    event_id UUID REFERENCES events(id),
    quantity INTEGER NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot additions
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100) UNIQUE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booked_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_source VARCHAR(20) DEFAULT 'webapp';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bookings_payment_ref ON bookings(payment_reference);
CREATE INDEX IF NOT EXISTS idx_bookings_phone ON bookings(phone);
```

#### Tickets Table (Extended)
```sql
-- Existing webapp fields
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID REFERENCES bookings(id),
    event_id UUID REFERENCES events(id),
    user_id UUID REFERENCES users(id),
    ticket_code VARCHAR(50) UNIQUE NOT NULL,
    qr_code_url TEXT,
    status VARCHAR(20) DEFAULT 'valid',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot additions for anonymous events
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS entry_code VARCHAR(50);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed BOOLEAN DEFAULT FALSE;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed_at TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ;
```

### Bot-Specific Tables

These tables are only used by the bot:

```sql
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

CREATE INDEX idx_conversations_phone ON conversations(phone);

-- Message logs for analytics
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

CREATE INDEX idx_message_logs_phone ON message_logs(phone);
CREATE INDEX idx_message_logs_created ON message_logs(created_at);

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

CREATE INDEX idx_anonymous_logs_event ON anonymous_access_logs(event_id);
```

## User Account Linking

### Phone Number as Primary Identifier

The bot uses phone numbers to identify users. When a user interacts via WhatsApp:

1. **First Time User**
   ```python
   # Bot creates user with phone number
   user = User(
       phone="+2348012345678",
       whatsapp_name="John Doe",
       # email and password are NULL (can be set later in webapp)
   )
   ```

2. **Existing Webapp User**
   ```python
   # User can link WhatsApp by adding phone in webapp settings
   # Bot will find existing user by phone
   user = await db.query(User).filter(User.phone == phone).first()
   ```

3. **Account Merging**
   ```python
   # If user signs up on webapp after using bot:
   # - Webapp prompts for phone number during signup
   # - System links existing bot bookings to webapp account
   # - User sees all their WhatsApp bookings in webapp
   ```

## Data Flow Examples

### Example 1: User Books via WhatsApp

```
1. User: "Book 2 tickets for Davido concert"
   ↓
2. Bot creates booking in shared database
   - booking.booking_source = 'whatsapp'
   - booking.phone = "+2348012345678"
   ↓
3. User pays via Paystack
   ↓
4. Bot generates tickets
   - tickets.qr_code_url stored in database
   ↓
5. User logs into webapp
   ↓
6. Webapp queries: SELECT * FROM bookings WHERE user_id = ?
   ↓
7. User sees WhatsApp booking in "My Tickets" section
```

### Example 2: Organizer Creates Event via WhatsApp

```
1. Organizer: "Create event"
   ↓
2. Bot guides through event creation
   ↓
3. Bot creates event in shared database
   - event.created_via = 'whatsapp'
   - event.host_id = organizer_user_id
   ↓
4. Organizer logs into webapp
   ↓
5. Webapp queries: SELECT * FROM events WHERE host_id = ?
   ↓
6. Organizer sees WhatsApp-created event
7. Can edit, view analytics, download reports
```

### Example 3: Cross-Platform Booking

```
1. User discovers event on webapp
   ↓
2. User shares event link to WhatsApp group
   ↓
3. Friend clicks link, opens webapp
   ↓
4. Friend prefers to book via WhatsApp
   ↓
5. Friend sends event ID to bot: "Book event #ABC123"
   ↓
6. Bot looks up event in shared database
   ↓
7. Bot processes booking
   ↓
8. Both users see their bookings in webapp
```

## Migration Script

Run this to add bot fields to existing webapp database:

```sql
-- migration_add_bot_fields.sql

-- Users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS location_preference GEOGRAPHY(POINT, 4326);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_categories TEXT[];
ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

-- Events table
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

-- Bookings table
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100) UNIQUE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booked_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_source VARCHAR(20) DEFAULT 'webapp';

-- Tickets table
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS entry_code VARCHAR(50);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed BOOLEAN DEFAULT FALSE;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS location_revealed_at TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ;

-- Create bot-specific tables
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    phone VARCHAR(20) NOT NULL,
    current_flow VARCHAR(50),
    flow_state JSONB,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_events_secret_code ON events(secret_code);
CREATE INDEX IF NOT EXISTS idx_events_anonymous ON events(is_anonymous, status);
CREATE INDEX IF NOT EXISTS idx_bookings_payment_ref ON bookings(payment_reference);
CREATE INDEX IF NOT EXISTS idx_bookings_phone ON bookings(phone);
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone);
CREATE INDEX IF NOT EXISTS idx_message_logs_phone ON message_logs(phone);
CREATE INDEX IF NOT EXISTS idx_message_logs_created ON message_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_anonymous_logs_event ON anonymous_access_logs(event_id);
```

## Webapp Updates Needed

### 1. User Profile - Add Phone Number Field

```javascript
// In user settings page
<input 
  type="tel" 
  placeholder="+234 XXX XXX XXXX"
  value={user.phone}
  onChange={handlePhoneUpdate}
/>
```

### 2. Bookings List - Show Source

```javascript
// In bookings list
{booking.booking_source === 'whatsapp' && (
  <Badge>📱 WhatsApp</Badge>
)}
```

### 3. Events List - Show Anonymous Badge

```javascript
// In events list
{event.is_anonymous && (
  <Badge>🔒 Secret Event</Badge>
)}
```

### 4. Event Details - Show Secret Code

```javascript
// For organizers viewing their events
{event.secret_code && (
  <div>
    <label>Secret Code:</label>
    <code>{event.secret_code}</code>
    <button onClick={copyToClipboard}>Copy</button>
  </div>
)}
```

## Configuration

### Bot Environment

```env
# Use same Supabase database as webapp
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Bot-specific
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_ACCESS_TOKEN=xxx
ANTHROPIC_API_KEY=xxx
PAYSTACK_SECRET_KEY=xxx
```

### Webapp Environment

```env
# Existing Supabase config
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=xxx

# No changes needed - bot uses same database
```

## Testing Integration

### 1. Create User via WhatsApp
```
WhatsApp: "Hi"
Bot: Creates user with phone number
```

### 2. Check Webapp
```
Login to webapp → Profile
Should see: phone number field (empty)
```

### 3. Link Accounts
```
Webapp: Add phone number in profile
Save
```

### 4. Book via WhatsApp
```
WhatsApp: "Book ticket"
Complete payment
```

### 5. Verify in Webapp
```
Webapp: My Tickets
Should see: WhatsApp booking with 📱 badge
```

## Security Considerations

### Row Level Security (RLS)

Enable RLS on Supabase to ensure users only see their own data:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Users can see their own bookings
CREATE POLICY "Users can view own bookings" ON bookings
  FOR SELECT USING (auth.uid() = user_id);

-- Users can see their own tickets
CREATE POLICY "Users can view own tickets" ON tickets
  FOR SELECT USING (auth.uid() = user_id);

-- Bot service role bypasses RLS
-- Use service_role key in bot for full access
```

### Bot Database Access

```python
# Bot uses service role key (bypasses RLS)
# This is safe because bot validates users via WhatsApp phone number

from app.config import settings

# Use direct PostgreSQL connection (not Supabase client)
DATABASE_URL = settings.DATABASE_URL  # Service role access
```

## Deployment

### 1. Run Migration

```bash
# Connect to Supabase database
psql $DATABASE_URL -f migration_add_bot_fields.sql
```

### 2. Deploy Bot

```bash
# Bot connects to same database
railway up
```

### 3. Update Webapp

```bash
# Deploy webapp with phone number field
netlify deploy --prod
```

### 4. Test End-to-End

```bash
# 1. Book via WhatsApp
# 2. Login to webapp
# 3. Verify booking appears
# 4. Create event in webapp
# 5. Book via WhatsApp
# 6. Verify in webapp
```

## Monitoring

### Track Cross-Platform Activity

```sql
-- Bookings by source
SELECT 
  booking_source,
  COUNT(*) as count,
  SUM(total_amount) as revenue
FROM bookings
WHERE status = 'confirmed'
GROUP BY booking_source;

-- Events by creation method
SELECT 
  created_via,
  COUNT(*) as count
FROM events
WHERE status = 'active'
GROUP BY created_via;

-- Users with phone numbers (bot users)
SELECT COUNT(*) FROM users WHERE phone IS NOT NULL;
```

---

**Key Takeaway**: The bot and webapp share the same database, ensuring a seamless experience across platforms. Users can start on WhatsApp and continue on the web, or vice versa, with all their data synced automatically.
