# Quick Test Reference

## 🚀 Fast Testing Commands

### Run Tests
```bash
# All tests
./run_tests.sh all

# With coverage
./run_tests.sh coverage

# Specific feature
./run_tests.sh registration
./run_tests.sh bookings
./run_tests.sh gifts

# Quick smoke test
./run_tests.sh quick
```

---

## 💬 WhatsApp Test Commands

### User Registration
```
Hi
John
Doe
john@test.com
profile
```

### Event Discovery
```
Events in Lagos
Near me
Concerts in Lagos
1
```

### Booking
```
Book 2
[Select payment]
My tickets
```

### Gift Tickets
```
Gift ticket
2
08012345678
Happy Birthday!
My gifts
```

### Organizer
```
Create event
Manage event
Stats 1
Broadcast 1
Edit 1
```

### Other Features
```
Share ticket
Request refund
promo SUMMER20
Recommend
Share
checkin GRV-ABC123
Analytics
Download report
```

---

## ✅ Quick Checklist

- [ ] User can register
- [ ] User can find events
- [ ] User can book tickets
- [ ] User receives QR codes
- [ ] User can share tickets
- [ ] User can request refunds
- [ ] Organizer can create events
- [ ] Organizer can manage events
- [ ] Gift tickets work
- [ ] Promo codes work
- [ ] All payments process
- [ ] All notifications sent

---

## 🐛 Common Issues

### Database Connection
```bash
# Check connection
psql -U postgres -d grooovy

# Reset database
dropdb test_grooovy
createdb test_grooovy
```

### Import Errors
```bash
# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt
```

### Test Failures
```bash
# Run with verbose output
pytest -v -s

# Run single test
pytest tests/test_bookings.py::test_create_booking_success

# Stop on first failure
pytest -x
```

---

## 📊 Test Results Format

```
✅ PASS - Feature works correctly
❌ FAIL - Feature has issues
⏳ PENDING - Not yet tested
⚠️ WARNING - Works but has minor issues
```

---

## 🎯 Priority Testing Order

1. User Registration
2. Event Discovery
3. Booking & Payment
4. Ticket Delivery
5. Share Ticket
6. Request Refund
7. Gift Tickets
8. Event Management
9. All other features

---

## 📞 Quick Help

**Issue:** Tests won't run
**Fix:** Check pytest installed, database connected

**Issue:** Import errors
**Fix:** Set PYTHONPATH, check file locations

**Issue:** Database errors
**Fix:** Check connection string, verify migrations

**Issue:** Async errors
**Fix:** Check event loop, use pytest-asyncio

---

**Status:** Ready for Testing! 🧪
