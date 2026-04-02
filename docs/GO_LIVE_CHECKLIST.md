# 🚀 Go Live Checklist - Make Your Bot Live in 1 Hour

## What You Need (Prerequisites)

### 1. API Accounts (Sign up for these first)
- [ ] **Meta Business Account** - https://business.facebook.com (FREE)
- [ ] **WhatsApp Business Account** - Via Meta Business (FREE for first 1,000 conversations/month)
- [ ] **Anthropic Account** - https://console.anthropic.com ($5 credit free)
- [ ] **Paystack Account** - https://paystack.com (FREE, 2.5% per transaction)
- [ ] **Cloudinary Account** - https://cloudinary.com (FREE tier: 25k transformations/month)
- [ ] **Railway Account** - https://railway.app (FREE $5 credit/month) OR Render.com

### 2. Your Existing Infrastructure
- [ ] **Grooovy Webapp** - Already running on Netlify
- [ ] **Supabase Database** - Already set up with webapp
- [ ] **Database Connection URL** - Get from Supabase dashboard

---

## Step-by-Step: Go Live in 60 Minutes

### PHASE 1: Get API Credentials (20 minutes)

#### A. WhatsApp Business API (10 min)
1. Go to https://developers.facebook.com
2. Click "My Apps" → "Create App"
3. Choose "Business" type
4. Add "WhatsApp" product
5. Go to WhatsApp → Getting Started
6. Note down:
   ```
   Phone Number ID: ___________________
   Business Account ID: _______________
   ```
7. Generate Permanent Access Token:
   - Click "Generate Token"
   - Copy and save: `WHATSAPP_ACCESS_TOKEN`
8. Get a phone number:
   - Use Meta's test number (FREE, limited to 5 test users)
   - OR buy Nigerian number (+234) and verify it

#### B. Anthropic API (3 min)
1. Go to https://console.anthropic.com
2. Sign up (get $5 free credit)
3. Go to API Keys
4. Create new key
5. Copy: `ANTHROPIC_API_KEY=sk-ant-...`

#### C. Paystack (3 min)
1. Go to https://dashboard.paystack.com
2. Sign up (Nigerian business)
3. Go to Settings → API Keys & Webhooks
4. Copy:
   ```
   PAYSTACK_SECRET_KEY=sk_live_...
   PAYSTACK_PUBLIC_KEY=pk_live_...
   ```
   (Use `sk_test_...` for testing first)

#### D. Cloudinary (2 min)
1. Go to https://cloudinary.com
2. Sign up (FREE)
3. Dashboard → Account Details
4. Copy:
   ```
   CLOUDINARY_CLOUD_NAME=___________
   CLOUDINARY_API_KEY=______________
   CLOUDINARY_API_SECRET=___________
   ```

#### E. Railway (2 min)
1. Go to https://railway.app
2. Sign up with GitHub
3. That's it! (We'll deploy later)

---

### PHASE 2: Prepare Database (10 minutes)

#### A. Get Supabase Database URL (2 min)
1. Go to your Supabase project
2. Settings → Database
3. Copy "Connection string" (URI format)
4. Replace `[YOUR-PASSWORD]` with your actual password
5. Save as: `DATABASE_URL`

#### B. Run Migration (5 min)
```bash
# On your local machine
cd grooovy-whatsapp-bot

# Install psql if not installed
# Mac: brew install postgresql
# Ubuntu: sudo apt-get install postgresql-client

# Run migration
psql "your-database-url-here" -f migrations/add_bot_fields.sql
```

Expected output:
```
ALTER TABLE
ALTER TABLE
CREATE TABLE
CREATE INDEX
...
NOTICE: Migration completed successfully!
```

#### C. Test Connection (3 min)
```bash
# Install dependencies
pip install -r requirements.txt

# Test database
python test_integration.py
```

Should see:
```
✅ Users table exists
✅ Events table exists
✅ Integration test completed successfully!
```

---

### PHASE 3: Configure & Deploy Bot (20 minutes)

#### A. Configure Environment (5 min)
```bash
# Create .env file
cp .env.example .env

# Edit .env
nano .env
```

Fill in ALL these values:
```env
# Database (SAME as webapp)
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
REDIS_URL=redis://default:[password]@[host]:6379

# WhatsApp (from Phase 1A)
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
VERIFY_TOKEN=any_random_string_you_choose

# AI (from Phase 1B)
ANTHROPIC_API_KEY=sk-ant-...

# Payments (from Phase 1C)
PAYSTACK_SECRET_KEY=sk_live_...  # Use sk_test_... for testing
PAYSTACK_PUBLIC_KEY=pk_live_...  # Use pk_test_... for testing

# Storage (from Phase 1D)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# App
APP_ENV=production
APP_URL=https://your-bot-url.com  # Will get this after deploy
WEBHOOK_BASE_URL=https://your-bot-url.com
SECRET_KEY=generate_random_32_char_string
```

#### B. Deploy to Railway (10 min)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init
# Name: grooovy-whatsapp-bot

# Add Redis (required for Celery)
railway add

# Choose: Redis

# Deploy
railway up

# Wait for deployment...
# ████████████████████ 100%

# Get your bot URL
railway domain
# Output: grooovy-bot-production.up.railway.app
```

#### C. Set Environment Variables in Railway (5 min)
```bash
# Set all variables from .env
railway variables set DATABASE_URL="your-database-url"
railway variables set WHATSAPP_PHONE_NUMBER_ID="..."
railway variables set WHATSAPP_ACCESS_TOKEN="..."
railway variables set VERIFY_TOKEN="..."
railway variables set ANTHROPIC_API_KEY="..."
railway variables set PAYSTACK_SECRET_KEY="..."
railway variables set PAYSTACK_PUBLIC_KEY="..."
railway variables set CLOUDINARY_CLOUD_NAME="..."
railway variables set CLOUDINARY_API_KEY="..."
railway variables set CLOUDINARY_API_SECRET="..."
railway variables set APP_ENV="production"
railway variables set SECRET_KEY="your-random-secret"

# Get Redis URL from Railway
railway variables
# Copy REDIS_URL value

railway variables set REDIS_URL="redis://..."
```

---

### PHASE 4: Configure Webhooks (10 minutes)

#### A. WhatsApp Webhook (5 min)
1. Go to Meta App Dashboard
2. WhatsApp → Configuration
3. Click "Edit" on Webhook
4. Set Callback URL:
   ```
   https://your-railway-url.up.railway.app/webhooks/whatsapp
   ```
5. Set Verify Token: (same as VERIFY_TOKEN in .env)
6. Click "Verify and Save"
7. Subscribe to fields:
   - ✅ messages
8. Should see ✅ "Webhook verified"

#### B. Paystack Webhook (3 min)
1. Go to Paystack Dashboard
2. Settings → Webhooks
3. Set Webhook URL:
   ```
   https://your-railway-url.up.railway.app/webhooks/paystack
   ```
4. Click "Save"

#### C. Test Webhooks (2 min)
```bash
# Check bot is running
curl https://your-railway-url.up.railway.app/health

# Should return:
# {"status":"healthy","timestamp":"2026-02-17T..."}
```

---

### PHASE 5: Test Live Bot (10 minutes)

#### A. Add Test Number (2 min)
1. Meta App Dashboard → WhatsApp → API Setup
2. Click "Add phone number"
3. Enter YOUR phone number
4. Verify with code sent to WhatsApp

#### B. Send First Message (1 min)
Open WhatsApp and send to your bot number:
```
Hi
```

Expected response:
```
👋 Welcome to Grooovy!

I'm your AI assistant for discovering and booking amazing events in Nigeria.

What can I help you with?
• Find events near you
• Book tickets
• View your tickets
• Unlock secret events

Try: "Concerts in Lagos this weekend" or "Help"
```

#### C. Test Full Flow (7 min)

**Test 1: Event Discovery**
```
You: Concerts in Lagos
Bot: [Shows list of events from your database]
```

**Test 2: Secret Event**
```
You: TECH2026
Bot: 🔓 Access Granted! [Shows secret event]
```

**Test 3: Booking (Use test card)**
```
You: Book 1 ticket
Bot: [Shows booking summary with payment buttons]
[Click payment link]
[Use Paystack test card: 4084084084084081]
Bot: 🎉 Payment Confirmed! [Sends QR code ticket]
```

**Test 4: View Tickets**
```
You: My tickets
Bot: [Shows your bookings]
```

**Test 5: Create Event**
```
You: Create event
Bot: [Guides through event creation]
```

---

## ✅ Final Verification

### Check These Work:
- [ ] Bot responds to "Hi"
- [ ] Can discover events
- [ ] Can unlock secret events with code
- [ ] Can book tickets
- [ ] Payment link works
- [ ] Tickets generated and sent
- [ ] WhatsApp bookings visible in webapp
- [ ] Can create events via WhatsApp
- [ ] Bot-created events visible in webapp

### Check Background Jobs:
```bash
# SSH into Railway or check logs
railway logs

# Should see Celery workers running:
# [INFO] celery@worker ready
# [INFO] celery beat running
```

---

## 🎉 You're Live!

### What to Do Next:

#### 1. Add More Test Users (5 min)
Meta App Dashboard → WhatsApp → API Setup → Add phone numbers
(Free tier: up to 5 test users)

#### 2. Go to Production (When ready)
1. Submit app for review (Meta)
2. Get approved (1-2 weeks)
3. Unlimited users!

#### 3. Promote Your Bot
- Add WhatsApp button to webapp
- Share bot number on social media
- Send to existing users via email
- Post in WhatsApp groups

#### 4. Monitor Usage
```bash
# Check logs
railway logs --follow

# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM message_logs"
```

---

## 💰 Costs (Monthly)

### Free Tier (0-1,000 users):
- WhatsApp: FREE (1,000 conversations/month)
- Railway: FREE ($5 credit)
- Anthropic: ~$10-20 (10k messages)
- Paystack: FREE (2.5% per transaction)
- Cloudinary: FREE (25k QR codes)

**Total: ~$10-20/month**

### Paid Tier (1,000-10,000 users):
- WhatsApp: ~$50 (10k conversations)
- Railway: ~$20
- Anthropic: ~$100
- Paystack: FREE (2.5% per transaction)
- Cloudinary: FREE

**Total: ~$170/month**

---

## 🆘 Troubleshooting

### Issue: Webhook verification fails
**Solution:**
```bash
# Check VERIFY_TOKEN matches in both places:
railway variables | grep VERIFY_TOKEN
# Should match what you entered in Meta dashboard
```

### Issue: Bot doesn't respond
**Solution:**
```bash
# Check logs
railway logs --follow

# Check if bot is running
curl https://your-url.up.railway.app/health
```

### Issue: Database connection error
**Solution:**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check DATABASE_URL is correct
railway variables | grep DATABASE_URL
```

### Issue: Payment not working
**Solution:**
- Check using test keys first: `sk_test_...`
- Verify Paystack webhook is set
- Check Paystack dashboard for errors

### Issue: QR codes not generating
**Solution:**
- Check Cloudinary credentials
- Verify API quota not exceeded
- Check Railway logs for errors

---

## 📞 Support

- **Meta/WhatsApp**: https://developers.facebook.com/support
- **Railway**: https://railway.app/help
- **Paystack**: support@paystack.com
- **Anthropic**: support@anthropic.com

---

## 🎊 Congratulations!

Your WhatsApp bot is now LIVE and integrated with your webapp!

Users can:
✅ Book tickets via WhatsApp
✅ See bookings in webapp
✅ Create events via WhatsApp
✅ Manage everything in webapp

**Next**: Scale to 10,000+ users and dominate Nigerian event ticketing! 🚀
