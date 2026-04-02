# Testing Guide

## Test Scenarios

### 1. Basic Flows

#### Greeting
```
You: Hi
Bot: 👋 Welcome to Grooovy! ...
```

#### Help
```
You: Help
Bot: 🤖 Grooovy Bot Help ...
```

### 2. Event Discovery

```
You: Concerts in Lagos
Bot: 🎵 Found X event(s): ...

You: 1
Bot: [Event details]

You: Book 2
Bot: 🎟️ Booking Summary ...
```

### 3. Secret Event Unlock

```
You: GROOVY2026
Bot: 🔓 Access Granted! ...
     [Event details with location reveal info]

You: Book 1
Bot: [Booking flow]
```

### 4. Booking & Payment

```
You: Book 2 tickets
Bot: 🎟️ Booking Summary ...
     [Payment method buttons]

[Click "💳 Card"]
Bot: 💳 Card Payment
     👉 [Paystack link]

[Complete payment on Paystack]
Bot: 🎉 Payment Confirmed!
     [QR code tickets sent]
```

### 5. View Tickets

```
You: My tickets
Bot: 🎫 Your Tickets (2):
     [List of tickets]
```

### 6. Event Creation (Organizer)

```
You: Create event
Bot: 🎉 Let's create your event! ...

You: Tech Founders Dinner
Bot: Great title! What type of event? ...

You: 7
Bot: 🤝 Networking event - perfect! When is the event? ...

You: 25/02/2026 at 6:30 PM
Bot: 📅 Tuesday, February 25, 2026 at 6:30 PM ...

[Continue through all steps]

You: 1
Bot: 🎉 Event Created Successfully! ...
```

## Automated Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ai_engine.py

# Run with coverage
pytest --cov=app tests/
```

### Test Payment Flow (Sandbox)

1. Use Paystack test keys in `.env`:
```
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
```

2. Test cards:
- Success: `4084084084084081`
- Decline: `5060666666666666666`
- CVV: `408` | Expiry: `12/30` | PIN: `0000`

### Test WhatsApp Webhook Locally

```bash
# Start ngrok
ngrok http 8000

# Update WhatsApp webhook URL in Meta dashboard
# Send test message to bot number
```

### Test Background Jobs

```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.celery_app beat --loglevel=info

# Trigger task manually
python -c "from app.tasks.bookings import cleanup_expired_bookings_task; cleanup_expired_bookings_task.delay()"
```

## Load Testing

### Simulate Multiple Users

```python
import asyncio
import httpx

async def simulate_user(user_id):
    async with httpx.AsyncClient() as client:
        # Simulate incoming message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": f"+234{user_id:010d}",
                            "id": f"msg_{user_id}",
                            "type": "text",
                            "text": {"body": "Hi"}
                        }],
                        "metadata": {}
                    }
                }]
            }]
        }
        
        response = await client.post(
            "http://localhost:8000/webhooks/whatsapp",
            json=payload
        )
        print(f"User {user_id}: {response.status_code}")

async def main():
    # Simulate 100 concurrent users
    tasks = [simulate_user(i) for i in range(100)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

## Monitoring

### Check Bot Health

```bash
curl http://localhost:8000/health
```

### View Logs

```bash
# API logs
tail -f logs/app.log

# Celery logs
tail -f logs/celery.log

# Database queries (if enabled)
tail -f logs/db.log
```

### Database Queries

```sql
-- Active bookings
SELECT status, COUNT(*) 
FROM bookings 
GROUP BY status;

-- Events by category
SELECT category, COUNT(*) 
FROM events 
WHERE status = 'active' 
GROUP BY category;

-- Tickets sold today
SELECT COUNT(*) 
FROM tickets 
WHERE DATE(created_at) = CURRENT_DATE;

-- Revenue today
SELECT SUM(total_amount) 
FROM bookings 
WHERE status = 'confirmed' 
AND DATE(confirmed_at) = CURRENT_DATE;
```

## Common Issues

### Issue: Webhook not receiving messages
**Solution:**
- Check ngrok is running
- Verify webhook URL in Meta dashboard
- Check signature verification is passing
- Look for errors in logs

### Issue: Payment not confirming
**Solution:**
- Check Paystack webhook is configured
- Verify webhook signature
- Check booking exists with payment reference
- Look for errors in Paystack dashboard

### Issue: QR codes not generating
**Solution:**
- Check Cloudinary credentials
- Verify API quota not exceeded
- Check image upload logs

### Issue: Location not revealing
**Solution:**
- Check Celery beat is running
- Verify event has correct reveal settings
- Check scheduled task logs
- Manually trigger: `process_location_reveals_task.delay()`

## Performance Benchmarks

Target metrics:
- Webhook response time: < 200ms
- AI classification: < 1s
- Payment initialization: < 2s
- Ticket generation: < 3s
- Message delivery: < 1s

Monitor with:
```python
# Add to message_log
response_time_ms = (end_time - start_time) * 1000
```
