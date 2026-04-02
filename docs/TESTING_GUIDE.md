# Grooovy WhatsApp Bot - Comprehensive Testing Guide

## Overview
This guide covers testing all 15 implemented features of the Grooovy WhatsApp bot.

---

## 🧪 Testing Setup

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Set up test database
createdb test_grooovy

# Run migrations on test database
# (Update connection string in tests/conftest.py)
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_user_registration.py

# Run specific test
pytest tests/test_bookings.py::test_create_booking_success

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

---

## 📋 Feature Testing Checklist

### ✅ 1. User Registration

**Test Cases:**
- [ ] New user says "Hi" → Registration flow starts
- [ ] Enter valid first name → Proceeds to last name
- [ ] Enter invalid first name (too short) → Error message
- [ ] Enter invalid first name (numbers) → Error message
- [ ] Enter valid last name → Proceeds to email
- [ ] Enter valid email → Account created
- [ ] Enter invalid email → Error message
- [ ] Enter duplicate email → Error message
- [ ] Skip email → Account created without email
- [ ] Existing user says "Hi" → Welcome back message
- [ ] View profile → Shows correct details
- [ ] Profile shows booking stats

**Manual Test Script:**
```
User: Hi
Bot: [Registration starts]

User: John
Bot: [Asks for last name]

User: Doe
Bot: [Asks for email]

User: john@example.com
Bot: [Account created, welcome message]

User: profile
Bot: [Shows profile with details]
```

---

### ✅ 2. Event Discovery

**Test Cases:**
- [ ] Search "Events in Lagos" → Shows events
- [ ] Search "Concerts near me" → Shows concerts
- [ ] Share location → Shows nearby events (20-mile radius)
- [ ] Events sorted by distance
- [ ] Distance displayed correctly
- [ ] Event capacity shown
- [ ] Price displayed
- [ ] Anonymous events show "Location hidden"
- [ ] Select event by number → Shows details
- [ ] No events found → Helpful message

**Manual Test Script:**
```
User: Events in Lagos
Bot: [Shows 5 events with details]

User: 2
Bot: [Shows full details of event #2]

User: Near me
Bot: [Asks for location or uses saved location]
```

---

### ✅ 3. Event Details View

**Test Cases:**
- [ ] Select event number → Full details shown
- [ ] Description displayed
- [ ] Date and time formatted correctly
- [ ] Location shown (or hidden for anonymous)
- [ ] Capacity and remaining tickets
- [ ] Price displayed
- [ ] Category shown
- [ ] Urgency indicators (low tickets)
- [ ] Call-to-action buttons
- [ ] Event saved to conversation state

**Manual Test Script:**
```
User: Events in Lagos
Bot: [Shows event list]

User: 1
Bot: [Shows full event details with all fields]
```

---

### ✅ 4. Booking & Payment

**Test Cases:**
- [ ] Say "Book 2" → Booking summary shown
- [ ] Payment methods displayed
- [ ] Select payment method → Paystack link
- [ ] Payment successful → Tickets delivered
- [ ] Payment failed → Error message
- [ ] Booking expires after 15 minutes
- [ ] Tickets reserved during booking
- [ ] Total calculated correctly
- [ ] Booking source tagged as "whatsapp"
- [ ] Email confirmation sent (if email provided)

**Manual Test Script:**
```
User: Book 2
Bot: [Shows booking summary with total]
Bot: [Payment method buttons]

User: [Clicks Card]
Bot: [Paystack payment link]

[After payment]
Bot: [Confirmation + QR codes]
```

---

### ✅ 5. View My Tickets

**Test Cases:**
- [ ] Say "My tickets" → Shows all tickets
- [ ] Ticket code displayed
- [ ] Event details shown
- [ ] QR code available
- [ ] Entry code shown (if applicable)
- [ ] No tickets → Helpful message
- [ ] Multiple tickets listed
- [ ] Sorted by date

**Manual Test Script:**
```
User: My tickets
Bot: [Lists all tickets with codes]

User: [Ticket code]
Bot: [Shows QR code image]
```

---

### ✅ 6. Share Ticket

**Test Cases:**
- [ ] Say "Share ticket" → Shows ticket list
- [ ] Select ticket number → Asks for recipient
- [ ] Enter valid phone → Ticket transferred
- [ ] Enter invalid phone → Error message
- [ ] Recipient receives ticket
- [ ] Recipient receives QR code
- [ ] Sender gets confirmation
- [ ] Ticket ownership updated
- [ ] Recipient account created if needed

**Manual Test Script:**
```
User: Share ticket
Bot: [Shows ticket list]

User: 1
Bot: [Asks for recipient phone]

User: 08012345678
Bot: [Confirms transfer]

[Recipient receives ticket]
```

---

### ✅ 7. Request Refund

**Test Cases:**
- [ ] Say "Request refund" → Shows bookings
- [ ] Select booking number → Shows confirmation
- [ ] Confirm refund → Refund processed
- [ ] Cancel refund → Booking remains active
- [ ] Refund amount correct
- [ ] Tickets cancelled
- [ ] Capacity released
- [ ] Refund notification sent
- [ ] Cannot refund past events

**Manual Test Script:**
```
User: Request refund
Bot: [Shows refundable bookings]

User: 1
Bot: [Shows refund details, asks confirmation]

User: Yes
Bot: [Processes refund, confirms]
```

---

### ✅ 8. Manage Event (Organizer)

**Test Cases:**
- [ ] Say "Manage event" → Shows organizer's events
- [ ] Event stats displayed (tickets sold, revenue)
- [ ] Management commands shown
- [ ] No events → Helpful message
- [ ] Multiple events listed
- [ ] Secret event indicator shown

**Manual Test Script:**
```
User: Manage event
Bot: [Shows event list with stats]
Bot: [Management command options]
```

---

### ✅ 9. Broadcast Messages

**Test Cases:**
- [ ] Say "Broadcast 1" → Asks for message
- [ ] Enter message → Sends to all attendees
- [ ] Delivery count shown
- [ ] No attendees → Error message
- [ ] Cancel broadcast → Aborted
- [ ] Message formatting preserved

**Manual Test Script:**
```
User: Manage event
Bot: [Shows events]

User: Broadcast 1
Bot: [Asks for message]

User: Event update: Gates open at 7 PM
Bot: [Sends to all, shows delivery count]
```

---

### ✅ 10. Analytics Dashboard

**Test Cases:**
- [ ] Say "Analytics" → Shows 30-day stats
- [ ] Total events displayed
- [ ] Total bookings shown
- [ ] Total revenue calculated
- [ ] Total tickets sold
- [ ] Top events listed
- [ ] No data → Shows zeros
- [ ] Stats accurate

**Manual Test Script:**
```
User: Analytics
Bot: [Shows comprehensive stats]
Bot: [Top 3 events by revenue]
```

---

### ✅ 11. Download Reports

**Test Cases:**
- [ ] Say "Download report" → Generates CSV
- [ ] Report includes all bookings
- [ ] All fields present
- [ ] Totals calculated correctly
- [ ] No events → Error message
- [ ] Report delivery confirmed

**Manual Test Script:**
```
User: Download report
Bot: [Generating report...]
Bot: [Report ready, sent to email]
```

---

### ✅ 12. Event Editing

**Test Cases:**
- [ ] Say "Edit 1" → Shows editable fields
- [ ] Select field → Asks for new value
- [ ] Enter valid value → Updated
- [ ] Enter invalid value → Error message
- [ ] Date change → Attendees notified
- [ ] Location change → Attendees notified
- [ ] Capacity cannot be less than sold
- [ ] Date cannot be in past

**Manual Test Script:**
```
User: Manage event
Bot: [Shows events]

User: Edit 1
Bot: [Shows editable fields 1-8]

User: 3
Bot: [Asks for new date]

User: 2026-04-15 19:00
Bot: [Updates, notifies attendees]
```

---

### ✅ 13. Check-in System

**Test Cases:**
- [ ] Say "checkin GRV-ABC123" → Checks in ticket
- [ ] Valid ticket → Success message
- [ ] Invalid ticket → Error message
- [ ] Already checked in → Error message
- [ ] Entry code required → Validates code
- [ ] Check-in timestamp recorded
- [ ] Attendee name shown

**Manual Test Script:**
```
User: checkin GRV-ABC123
Bot: [Checks in ticket, shows success]

User: checkin GRV-ABC123
Bot: [Already checked in error]
```

---

### ✅ 14. Multi-tier Tickets

**Test Cases:**
- [ ] Event with tiers → Shows tier options
- [ ] Tier prices displayed
- [ ] Tier capacity shown
- [ ] Select tier → Books from that tier
- [ ] Sold-out tier → Not available
- [ ] Time-based availability works
- [ ] Tier pricing calculated correctly

**Manual Test Script:**
```
User: Events in Lagos
Bot: [Shows event with tiers]

User: 1
Bot: [Shows tier options: VIP, Regular, Early Bird]

User: Book 1 2
Bot: [Books 2 VIP tickets]
```

---

### ✅ 15. Promo Codes

**Test Cases:**
- [ ] Say "promo SUMMER20" → Validates code
- [ ] Valid code → Discount applied
- [ ] Invalid code → Error message
- [ ] Expired code → Error message
- [ ] Max uses reached → Error message
- [ ] Minimum tickets not met → Error message
- [ ] Percentage discount calculated correctly
- [ ] Fixed discount applied correctly
- [ ] Max discount cap enforced

**Manual Test Script:**
```
User: [Select event]

User: promo SUMMER20
Bot: [Validates code, shows discount]

User: Book 2
Bot: [Applies discount at checkout]
```

---

### ✅ 16. AI Recommendations

**Test Cases:**
- [ ] Say "Recommend" → Shows personalized events
- [ ] New user → Shows popular events
- [ ] Returning user → Shows based on history
- [ ] Categories matched
- [ ] Price range matched
- [ ] Location-aware (if available)
- [ ] No recommendations → Helpful message

**Manual Test Script:**
```
User: Recommend
Bot: [Shows 5 personalized recommendations]
Bot: [Based on your interests: concerts]
```

---

### ✅ 17. Social Sharing

**Test Cases:**
- [ ] Say "Share" → Shows share options
- [ ] Share message formatted correctly
- [ ] Platform links generated
- [ ] Referral code included
- [ ] Share tracked
- [ ] All platforms available

**Manual Test Script:**
```
User: [Select event]

User: Share
Bot: [Shows formatted share message]
Bot: [Platform-specific links]
```

---

### ✅ 18. Gift Tickets

**Test Cases:**
- [ ] Say "Gift ticket" → Starts gift flow
- [ ] Enter quantity → Proceeds
- [ ] Enter recipient phone → Validates
- [ ] Add message → Optional
- [ ] Skip message → Continues
- [ ] Payment → Gift delivered
- [ ] Recipient receives gift
- [ ] Recipient receives QR codes
- [ ] Sender notified
- [ ] Cannot gift to self
- [ ] Gift history tracked

**Manual Test Script:**
```
User: [Select event]

User: Gift ticket
Bot: [Asks for quantity]

User: 2
Bot: [Asks for recipient phone]

User: 08012345678
Bot: [Asks for message]

User: Happy Birthday! 🎉
Bot: [Shows summary, payment]

[After payment]
Bot (to sender): [Gift delivered confirmation]
Bot (to recipient): [Gift notification + QR codes]

User: My gifts
Bot: [Shows gift history]
```

---

## 🔄 Integration Testing

### End-to-End Flows

#### Flow 1: Complete Booking Journey
```
1. User: Hi
2. Bot: [Registration]
3. User: [Complete registration]
4. User: Events in Lagos
5. Bot: [Shows events]
6. User: 1
7. Bot: [Event details]
8. User: Book 2
9. Bot: [Payment options]
10. User: [Complete payment]
11. Bot: [Tickets delivered]
12. User: My tickets
13. Bot: [Shows tickets]
```

#### Flow 2: Organizer Journey
```
1. User: Create event
2. Bot: [Event creation flow]
3. User: [Complete event creation]
4. User: Manage event
5. Bot: [Shows event with stats]
6. User: Stats 1
7. Bot: [Detailed statistics]
8. User: Broadcast 1
9. Bot: [Sends message to attendees]
```

#### Flow 3: Gift Journey
```
1. User: Events near me
2. Bot: [Shows events]
3. User: 2
4. Bot: [Event details]
5. User: Gift ticket
6. Bot: [Gift flow]
7. User: [Complete gift purchase]
8. Recipient: [Receives gift]
9. User: My gifts
10. Bot: [Shows gift history]
```

---

## 🐛 Error Handling Tests

### Test Error Scenarios
- [ ] Invalid phone number format
- [ ] Expired session
- [ ] Sold-out event
- [ ] Payment failure
- [ ] Network timeout
- [ ] Invalid promo code
- [ ] Insufficient capacity
- [ ] Past event date
- [ ] Invalid ticket code
- [ ] Duplicate check-in

---

## 📊 Performance Testing

### Load Tests
```bash
# Test concurrent bookings
# Test message throughput
# Test database queries
# Test API response times
```

### Metrics to Track
- Response time < 2 seconds
- Database queries < 50ms
- Concurrent users: 100+
- Message delivery rate: 99%+

---

## 🔒 Security Testing

### Security Checks
- [ ] SQL injection prevention
- [ ] Input validation
- [ ] Phone number verification
- [ ] Payment security
- [ ] Data encryption
- [ ] Access control
- [ ] Rate limiting

---

## 📝 Test Results Template

```markdown
## Test Run: [Date]

### Summary
- Total Tests: X
- Passed: X
- Failed: X
- Skipped: X
- Coverage: X%

### Failed Tests
1. [Test name] - [Reason]
2. [Test name] - [Reason]

### Issues Found
1. [Issue description]
2. [Issue description]

### Next Steps
1. [Action item]
2. [Action item]
```

---

## 🎯 Testing Priorities

### Priority 1 (Critical)
1. User registration
2. Event discovery
3. Booking & payment
4. Ticket delivery

### Priority 2 (Important)
5. Share ticket
6. Request refund
7. Event creation
8. Check-in system

### Priority 3 (Nice-to-Have)
9. Gift tickets
10. Promo codes
11. Recommendations
12. Social sharing

---

## 🚀 Pre-Launch Testing

### Final Checklist
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Manual testing complete
- [ ] Performance tests passed
- [ ] Security audit done
- [ ] Error handling verified
- [ ] Documentation updated
- [ ] Staging environment tested
- [ ] Production deployment plan ready

---

## 📞 Support During Testing

### Common Issues
1. **Database connection errors** - Check connection string
2. **Import errors** - Verify Python path
3. **Async errors** - Check event loop setup
4. **Test data conflicts** - Use test database

### Getting Help
- Check test logs
- Review error messages
- Consult documentation
- Ask for assistance

---

## ✅ Testing Complete

Once all tests pass:
1. Generate coverage report
2. Document any issues
3. Create test summary
4. Proceed to deployment

**Status:** Ready for comprehensive testing! 🧪
