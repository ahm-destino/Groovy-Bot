# Simple Setup Guide - 4 Steps to Go Live

## What You Need to Get

### 1. WhatsApp Business API (FREE)
- Go to: https://developers.facebook.com
- Create app → Add WhatsApp
- Get: Phone Number ID, Access Token

### 2. AI API ($5 free credit)
- Go to: https://console.anthropic.com
- Sign up
- Get: API Key

### 3. Payment API (FREE)
- Go to: https://paystack.com
- Sign up
- Get: Secret Key, Public Key

### 4. Image Storage (FREE)
- Go to: https://cloudinary.com
- Sign up
- Get: Cloud Name, API Key, API Secret

---

## 4 Steps to Go Live

### Step 1: Prepare Database (5 min)
```bash
# Run this command with your Supabase database URL
psql "your-supabase-url" -f migrations/add_bot_fields.sql
```

### Step 2: Configure Bot (5 min)
```bash
# Create config file
cp .env.example .env

# Edit and add all your API keys
nano .env
```

### Step 3: Deploy (10 min)
```bash
# Install Railway
npm install -g @railway/cli

# Deploy
railway login
railway init
railway add  # Choose Redis
railway up

# Set all environment variables
railway variables set DATABASE_URL="..."
railway variables set WHATSAPP_ACCESS_TOKEN="..."
# ... (set all variables from .env)
```

### Step 4: Connect WhatsApp (5 min)
1. Go to Meta App Dashboard
2. WhatsApp → Configuration → Webhook
3. Set URL: `https://your-railway-url.up.railway.app/webhooks/whatsapp`
4. Set Verify Token (from your .env)
5. Click "Verify and Save"

---

## Test It!

Send to your WhatsApp bot:
```
Hi
```

Should get:
```
👋 Welcome to Grooovy!
...
```

---

## That's It! 🎉

Your bot is live and connected to your webapp!

**Full details**: See [GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md)
