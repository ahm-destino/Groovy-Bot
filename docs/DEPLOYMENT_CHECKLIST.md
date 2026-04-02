# Deployment Checklist

## Pre-Deployment

### 1. API Credentials ✓
- [ ] WhatsApp Business Account created
- [ ] WhatsApp Phone Number verified
- [ ] Meta App created with WhatsApp product
- [ ] Permanent Access Token generated
- [ ] Anthropic API key obtained
- [ ] Paystack account created (use live keys for production)
- [ ] Cloudinary account created

### 2. Environment Setup ✓
- [ ] `.env` file configured with all credentials
- [ ] Database URL set (production PostgreSQL)
- [ ] Redis URL set (production Redis)
- [ ] Webhook base URL set (your domain)
- [ ] Secret key generated (use strong random string)

### 3. Database ✓
- [ ] PostgreSQL 15+ with PostGIS extension
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Database backups configured
- [ ] Connection pooling configured

### 4. Testing ✓
- [ ] All core flows tested locally
- [ ] Payment flow tested with Paystack test keys
- [ ] WhatsApp webhook tested with ngrok
- [ ] Background jobs tested
- [ ] Load testing completed

## Deployment Steps

### Option A: Railway.app (Recommended)

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Add databases
railway add --database postgres
railway add --database redis

# 5. Deploy
railway up

# 6. Set environment variables
railway variables set WHATSAPP_PHONE_NUMBER_ID=xxx
railway variables set WHATSAPP_ACCESS_TOKEN=xxx
railway variables set VERIFY_TOKEN=xxx
railway variables set ANTHROPIC_API_KEY=xxx
railway variables set PAYSTACK_SECRET_KEY=xxx
railway variables set PAYSTACK_PUBLIC_KEY=xxx
railway variables set CLOUDINARY_CLOUD_NAME=xxx
railway variables set CLOUDINARY_API_KEY=xxx
railway variables set CLOUDINARY_API_SECRET=xxx
railway variables set SECRET_KEY=xxx

# 7. Get deployment URL
railway domain

# 8. Run migrations
railway run alembic upgrade head
```

### Option B: Render.com

1. Create new Web Service
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL database
6. Add Redis instance
7. Set environment variables
8. Deploy

### Option C: Docker + VPS

```bash
# 1. Build image
docker build -t grooovy-bot .

# 2. Push to registry
docker tag grooovy-bot your-registry/grooovy-bot
docker push your-registry/grooovy-bot

# 3. On VPS: Pull and run
docker pull your-registry/grooovy-bot
docker-compose -f docker-compose.prod.yml up -d
```

## Post-Deployment

### 1. Configure WhatsApp Webhook ✓
- [ ] Go to Meta App Dashboard → WhatsApp → Configuration
- [ ] Set Webhook URL: `https://your-domain.com/webhooks/whatsapp`
- [ ] Set Verify Token (same as in .env)
- [ ] Subscribe to `messages` field
- [ ] Click "Verify and Save"
- [ ] Test by sending message to bot

### 2. Configure Paystack Webhook ✓
- [ ] Go to Paystack Dashboard → Settings → Webhooks
- [ ] Set Webhook URL: `https://your-domain.com/webhooks/paystack`
- [ ] Save webhook
- [ ] Test payment flow

### 3. Start Background Workers ✓
```bash
# If using Railway
railway run celery -A app.celery_app worker --loglevel=info
railway run celery -A app.celery_app beat --loglevel=info

# If using Docker
# Already included in docker-compose.prod.yml
```

### 4. Monitoring Setup ✓
- [ ] Set up error tracking (Sentry)
- [ ] Configure logging (CloudWatch/Papertrail)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Configure alerts (email/Slack)

### 5. Performance Optimization ✓
- [ ] Enable Redis caching
- [ ] Configure CDN for QR codes
- [ ] Set up database connection pooling
- [ ] Enable gzip compression

### 6. Security ✓
- [ ] HTTPS enabled (SSL certificate)
- [ ] Webhook signature verification enabled
- [ ] Rate limiting configured
- [ ] CORS configured properly
- [ ] Environment variables secured
- [ ] Database credentials rotated

## Testing Production

### 1. Basic Flows ✓
```
Test User: [Your WhatsApp number]

1. Send: "Hi"
   Expected: Welcome message

2. Send: "Help"
   Expected: Help menu

3. Send: "Concerts in Lagos"
   Expected: Event list (if events exist)

4. Create test event:
   Send: "Create event"
   Follow prompts

5. Test booking flow:
   Send: "Book 1 ticket"
   Complete payment

6. Check ticket delivery:
   Should receive QR code
```

### 2. Payment Testing ✓
- [ ] Test card payment (use real card in production)
- [ ] Test bank transfer
- [ ] Test USSD
- [ ] Verify webhook receives payment confirmation
- [ ] Verify tickets are generated and sent

### 3. Background Jobs ✓
- [ ] Verify expired bookings are cleaned up
- [ ] Test location reveal (create event with 1hr reveal)
- [ ] Test reminders (create event 24hrs away)

## Launch Checklist

### Pre-Launch ✓
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Support email/phone set up
- [ ] Terms of service ready
- [ ] Privacy policy ready
- [ ] Refund policy defined

### Launch Day ✓
- [ ] Announce on social media
- [ ] Send to WhatsApp groups
- [ ] Email existing Grooovy users
- [ ] Partner with 5-10 event organizers
- [ ] Monitor error logs closely
- [ ] Be ready for support requests

### Post-Launch (Week 1) ✓
- [ ] Monitor daily active users
- [ ] Track conversion rates
- [ ] Collect user feedback
- [ ] Fix critical bugs immediately
- [ ] Optimize slow queries
- [ ] Scale infrastructure if needed

## Scaling Checklist

### When you hit 1,000 users:
- [ ] Upgrade database plan
- [ ] Add Redis caching
- [ ] Enable CDN
- [ ] Set up load balancer

### When you hit 10,000 users:
- [ ] Horizontal scaling (multiple workers)
- [ ] Database read replicas
- [ ] Message queue optimization
- [ ] Consider microservices

## Rollback Plan

If something goes wrong:

```bash
# 1. Revert to previous deployment
railway rollback

# 2. Check logs
railway logs

# 3. Fix issue locally
# 4. Test thoroughly
# 5. Redeploy

# Emergency: Disable bot
# Set VERIFY_TOKEN to different value in Meta dashboard
# This will stop webhook from accepting messages
```

## Support Contacts

- WhatsApp API: https://developers.facebook.com/support
- Paystack: support@paystack.com
- Anthropic: support@anthropic.com
- Railway: https://railway.app/help

## Success Metrics to Track

Daily:
- Active users
- Messages processed
- Bookings created
- Payments completed
- Error rate
- Response time

Weekly:
- New users
- Revenue (GMV)
- Conversion rate
- User retention
- Popular events
- Support tickets

Monthly:
- Total users
- Total events
- Total tickets sold
- Total revenue
- CSAT score
- Churn rate

---

**Remember**: Start small, test thoroughly, scale gradually. Good luck! 🚀
