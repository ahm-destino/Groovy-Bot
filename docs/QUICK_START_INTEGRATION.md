# Quick Start: Integrating Bot with Existing Webapp

## Prerequisites

- Existing Grooovy webapp running on Netlify
- Supabase database with users, events, bookings, tickets tables
- Database connection URL

## Step 1: Run Database Migration (5 minutes)

```bash
# Get your Supabase database URL
# Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Run migration to add bot fields
psql "your-database-url" -f migrations/add_bot_fields.sql
```

This adds:
- `phone` column to users table
- Anonymous event fields to events table
- Payment tracking fields to bookings table
- Bot-specific tables (conversations, message_logs)

## Step 2: Configure Bot Environment (2 minutes)

```bash
# Copy example env
cp .env.example .env

# Edit .env
nano .env
```

Set these values:
```env
# Use SAME database as webapp
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# WhatsApp credentials
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_token
VERIFY_TOKEN=your_verify_token

# AI & Payments
ANTHROPIC_API_KEY=sk-ant-...
PAYSTACK_SECRET_KEY=sk_live_...  # Use live keys for production
CLOUDINARY_CLOUD_NAME=your_cloud
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
```

## Step 3: Test Integration (3 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Test database connection
python test_integration.py
```

Expected output:
```
✅ Users table exists
✅ Events table exists
✅ Bookings table exists
✅ Created test user
✅ Created test event (via bot)
✅ Created test booking (via bot)
✅ Integration test completed successfully!
```

## Step 4: Deploy Bot (10 minutes)

### Option A: Railway (Recommended)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway add --database postgres  # Skip if using existing Supabase
railway add --database redis
railway up

# Set environment variables
railway variables set DATABASE_URL="your-supabase-url"
railway variables set WHATSAPP_ACCESS_TOKEN="..."
# ... (set all variables)

# Get bot URL
railway domain
```

### Option B: Docker

```bash
# Build and run
docker-compose up -d
```

## Step 5: Configure WhatsApp Webhook (5 minutes)

1. Go to Meta App Dashboard → WhatsApp → Configuration
2. Set Webhook URL: `https://your-bot-url.com/webhooks/whatsapp`
3. Set Verify Token (same as in .env)
4. Subscribe to `messages`
5. Click "Verify and Save"

## Step 6: Test End-to-End (5 minutes)

### Test 1: Book via WhatsApp, View in Webapp

```
1. Send to WhatsApp bot: "Hi"
2. Bot: Welcome message
3. Send: "Concerts in Lagos"
4. Bot: Shows events (from shared database)
5. Book a ticket
6. Login to webapp
7. Go to "My Tickets"
8. ✅ Should see WhatsApp booking with 📱 badge
```

### Test 2: Create Event in Webapp, Book via WhatsApp

```
1. Login to webapp
2. Create new event
3. Copy event title
4. Send to WhatsApp bot: "Book [event title]"
5. Bot: Shows event details
6. Complete booking
7. Refresh webapp
8. ✅ Should see booking in event dashboard
```

### Test 3: Secret Event

```
1. Send to bot: "Create event"
2. Follow prompts, choose "Secret event"
3. Bot creates event with secret code
4. Login to webapp
5. Go to "My Events"
6. ✅ Should see event with 🔒 badge and secret code
```

## Step 7: Update Webapp UI (Optional, 30 minutes)

Add these features to webapp for better integration:

### 1. User Profile - Phone Number Field

```javascript
// In user settings page
<div>
  <label>WhatsApp Number</label>
  <input 
    type="tel" 
    placeholder="+234 XXX XXX XXXX"
    value={user.phone}
    onChange={updatePhone}
  />
  <p>Link your WhatsApp to see bot bookings here</p>
</div>
```

### 2. Bookings List - Source Badge

```javascript
// In bookings list component
{booking.booking_source === 'whatsapp' && (
  <Badge color="green">
    📱 WhatsApp
  </Badge>
)}
```

### 3. Events List - Anonymous Badge

```javascript
// In events list
{event.is_anonymous && (
  <Badge color="purple">
    🔒 Secret Event
  </Badge>
)}
```

### 4. Event Details - Secret Code Display

```javascript
// For organizers viewing their events
{event.secret_code && (
  <div className="secret-code">
    <label>Secret Code (share with invitees):</label>
    <code>{event.secret_code}</code>
    <button onClick={() => copyToClipboard(event.secret_code)}>
      Copy
    </button>
  </div>
)}
```

### 5. Analytics Dashboard

```javascript
// Add to organizer dashboard
const stats = await supabase
  .from('bookings')
  .select('booking_source, count')
  .eq('status', 'confirmed')
  .group('booking_source');

// Display:
// 📱 WhatsApp: 45 bookings
// 💻 Webapp: 32 bookings
```

## Verification Checklist

- [ ] Migration ran successfully
- [ ] Bot connects to database
- [ ] Test integration script passes
- [ ] Bot deployed and running
- [ ] WhatsApp webhook verified
- [ ] Can book via WhatsApp
- [ ] WhatsApp bookings visible in webapp
- [ ] Can create events via WhatsApp
- [ ] Bot-created events visible in webapp
- [ ] Secret events work end-to-end
- [ ] Payment flow works
- [ ] Tickets generated and sent
- [ ] Location reveals work (for anonymous events)
- [ ] Reminders sent

## Troubleshooting

### Issue: Bot can't connect to database
```bash
# Check DATABASE_URL is correct
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: WhatsApp bookings not showing in webapp
```bash
# Check if booking_source is set
psql $DATABASE_URL -c "SELECT id, booking_source FROM bookings LIMIT 5"

# Should see 'whatsapp' for bot bookings
```

### Issue: Migration fails
```bash
# Check if tables exist
psql $DATABASE_URL -c "\dt"

# If users table doesn't exist, you need to create webapp schema first
```

### Issue: User accounts not linking
```bash
# Check phone numbers
psql $DATABASE_URL -c "SELECT id, email, phone FROM users WHERE phone IS NOT NULL"

# Users need to add phone number in webapp settings to link accounts
```

## Next Steps

1. ✅ Integration complete
2. Monitor usage in both platforms
3. Add phone number field to webapp signup
4. Promote WhatsApp bot to existing users
5. Track cross-platform conversion rates
6. Optimize based on analytics

## Support

- Integration Guide: [WEBAPP_INTEGRATION.md](WEBAPP_INTEGRATION.md)
- Setup Guide: [docs/SETUP.md](docs/SETUP.md)
- Testing Guide: [docs/TESTING.md](docs/TESTING.md)

---

**Total Setup Time: ~30 minutes**

Your bot is now fully integrated with the webapp! 🎉
