# Grooovy WhatsApp Bot - Setup Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional, for local dev)
- Meta Business Account
- WhatsApp Business Account
- Anthropic API key
- Paystack account

## Step 1: WhatsApp Business API Setup

### 1.1 Create Meta Business Account
1. Go to [Meta Business Suite](https://business.facebook.com)
2. Create a new business account
3. Verify your business

### 1.2 Create WhatsApp Business App
1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create new app → Type: **Business**
3. Add **WhatsApp** product
4. Note down:
   - Phone Number ID
   - Business Account ID
   - Access Token (generate permanent token)

### 1.3 Get a Phone Number
- Use Meta's test number (free, limited)
- OR buy a Nigerian number (+234) and register it
- Verify the number

### 1.4 Configure Webhook
1. In WhatsApp settings, go to **Configuration**
2. Set webhook URL: `https://your-domain.com/webhooks/whatsapp`
3. Set verify token: (any random string, save it)
4. Subscribe to: `messages`

## Step 2: Get API Keys

### 2.1 Anthropic (Claude AI)
1. Go to [Anthropic Console](https://console.anthropic.com)
2. Create API key
3. Note down: `sk-ant-...`

### 2.2 Paystack
1. Go to [Paystack Dashboard](https://dashboard.paystack.com)
2. Settings → API Keys & Webhooks
3. Note down:
   - Secret Key: `sk_test_...`
   - Public Key: `pk_test_...`

### 2.3 Cloudinary (Optional, for QR codes)
1. Go to [Cloudinary](https://cloudinary.com)
2. Sign up for free account
3. Note down:
   - Cloud Name
   - API Key
   - API Secret

## Step 3: Local Development Setup

### 3.1 Clone & Install
```bash
# Clone repository
git clone <your-repo>
cd grooovy-whatsapp-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3.2 Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Fill in all the values from Step 1 and Step 2.

### 3.3 Start Database (Docker)
```bash
# Start PostgreSQL + Redis
docker-compose up -d db redis

# Wait for DB to be ready (10 seconds)
sleep 10
```

### 3.4 Run Migrations
```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### 3.5 Start Development Server
```bash
# Terminal 1: API server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Background worker (optional for now)
celery -A app.celery worker --loglevel=info
```

## Step 4: Expose Webhook (for testing)

WhatsApp needs a public HTTPS URL. Use one of these:

### Option A: ngrok (Easiest for testing)
```bash
# Install ngrok
brew install ngrok  # macOS
# OR download from https://ngrok.com

# Start tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update WhatsApp webhook URL to: https://abc123.ngrok.io/webhooks/whatsapp
```

### Option B: Railway.app (Production-ready)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Add database
railway add --database postgres
railway add --database redis

# Deploy
railway up

# Set environment variables
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set WHATSAPP_ACCESS_TOKEN=...
# ... (set all variables from .env)

# Get deployment URL
railway domain
```

## Step 5: Test the Bot

### 5.1 Verify Webhook
1. In Meta App Dashboard → WhatsApp → Configuration
2. Click "Verify and Save" on webhook URL
3. Should see ✅ success

### 5.2 Send Test Message
1. Add your phone number to WhatsApp test numbers
2. Send message to bot: "Hi"
3. Should receive welcome message

### 5.3 Test Flows
```
You: Hi
Bot: Welcome to Grooovy! ...

You: Help
Bot: Grooovy Bot Help ...

You: Concerts in Lagos
Bot: Found X events ...

You: GROOVY2026
Bot: 🔓 Access Granted! ...
```

## Step 6: Seed Test Data (Optional)

Create some test events:

```bash
# Run Python shell
python

# Create test event
from app.database import AsyncSessionLocal
from app.models import Event
from datetime import datetime, timedelta
import asyncio

async def create_test_event():
    async with AsyncSessionLocal() as db:
        event = Event(
            title="Davido Live in Concert",
            description="Amazing concert",
            category="concert",
            event_date=datetime.now() + timedelta(days=7),
            venue_name="Eko Convention Centre",
            full_address="Eko Atlantic, Victoria Island, Lagos",
            location_lat=6.4281,
            location_lng=3.4219,
            capacity=5000,
            tickets_sold=2347,
            ticket_price=15000,
            status="active"
        )
        db.add(event)
        await db.commit()
        print(f"Created event: {event.id}")

asyncio.run(create_test_event())
```

## Troubleshooting

### Webhook not receiving messages
- Check ngrok is running
- Verify webhook URL in Meta dashboard
- Check server logs: `tail -f logs/app.log`
- Test webhook manually: `curl -X POST https://your-url/webhooks/whatsapp`

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose ps`
- Check DATABASE_URL in .env
- Test connection: `psql $DATABASE_URL`

### AI not responding
- Check ANTHROPIC_API_KEY is valid
- Check API quota: https://console.anthropic.com
- Look for errors in logs

### WhatsApp rate limits
- Free tier: 1,000 conversations/month
- Upgrade to Business tier for more
- See: https://developers.facebook.com/docs/whatsapp/pricing

## Next Steps

1. ✅ Basic bot working
2. 📝 Implement payment flow (Paystack)
3. 🎫 Add ticket generation (QR codes)
4. 🔒 Build anonymous events features
5. ⏰ Set up background jobs (reminders, reveals)
6. 📊 Add analytics dashboard
7. 🚀 Deploy to production

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Email: support@grooovy.app
