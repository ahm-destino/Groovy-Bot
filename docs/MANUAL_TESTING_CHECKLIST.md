# Manual Testing Checklist

## 📋 Complete Feature Testing Checklist

Use this checklist to manually test all features via WhatsApp.

---

## Setup

- [ ] WhatsApp Business API configured
- [ ] Bot webhook URL set
- [ ] Test phone number ready
- [ ] Database seeded with test data
- [ ] Payment gateway in test mode

---

## 1. User Registration ✅

### New User Flow
- [ ] Send "Hi" to bot
- [ ] Receive welcome message
- [ ] Enter first name: "John"
- [ ] Receive confirmation, asked for last name
- [ ] Enter last name: "Doe"
- [ ] Receive confirmation, asked for email
- [ ] Enter email: "john.doe@test.com"
- [ ] Receive account created message
- [ ] Verify welcome message with features

### Validation Tests
- [ ] Try first name with 1 character → Error
- [ ] Try first name with numbers → Error
- [ ] Try invalid email format → Error
- [ ] Try duplicate email → Error
- [ ] Skip email → Account created without email

### Existing User
- [ ] Send "Hi" again
- [ ] Receive "Welcome back" message
- [ ] No registration prompt

### Profile Management
- [ ] Send "profile"
- [ ] Verify name, phone, email displayed
- [ ] Verify member since date
- [ ] Verify booking stats (if any)

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 2. Event Discovery ✅

### Location Search
- [ ] Send "Events in Lagos"
- [ ] Receive list of 5 events
- [ ] Verify event details (title, date, venue, price)
- [ ] Verify distance shown
- [ ] Verify capacity remaining

### Category Search
- [ ] Send "Concerts in Lagos"
- [ ] Receive only concert events
- [ ] Send "Parties near me"
- [ ] Receive only party events

### Location Sharing
- [ ] Share location via WhatsApp
- [ ] Receive events within 20 miles
- [ ] Verify sorted by distance
- [ ] Verify distance calculations accurate

### No Results
- [ ] Search for non-existent location
- [ ] Receive helpful "no events found" message
- [ ] Receive suggestions to try different search

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 3. Event Details View ✅

### View Details
- [ ] From event list, send "1"
- [ ] Receive full event details
- [ ] Verify description shown
- [ ] Verify date/time formatted correctly
- [ ] Verify location (or "hidden" for anonymous)
- [ ] Verify capacity and remaining tickets
- [ ] Verify price
- [ ] Verify category
- [ ] Verify call-to-action

### Anonymous Events
- [ ] View anonymous event details
- [ ] Verify location shows "Hidden"
- [ ] Verify reveal timing shown
- [ ] Verify entry code info shown

### Urgency Indicators
- [ ] View event with < 10 tickets
- [ ] Verify "Only X tickets left!" shown
- [ ] View event with < 50 tickets
- [ ] Verify "Selling fast!" shown

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 4. Booking & Payment ✅

### Standard Booking
- [ ] After viewing event, send "Book 2"
- [ ] Receive booking summary
- [ ] Verify quantity: 2
- [ ] Verify total amount correct
- [ ] Receive payment method buttons
- [ ] Click "Card" button
- [ ] Receive Paystack payment link
- [ ] Complete payment (test mode)
- [ ] Receive payment confirmation
- [ ] Receive QR code tickets (2x)

### Validation
- [ ] Try booking 0 tickets → Error
- [ ] Try booking more than available → Error
- [ ] Try booking without selecting event → Error

### Payment Methods
- [ ] Test Card payment
- [ ] Test Bank Transfer
- [ ] Test USSD

### Booking Expiry
- [ ] Create booking
- [ ] Wait 15+ minutes without payment
- [ ] Verify booking expires
- [ ] Verify tickets released

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 5. View My Tickets ✅

### View Tickets
- [ ] Send "My tickets"
- [ ] Receive list of all tickets
- [ ] Verify ticket codes shown
- [ ] Verify event details shown
- [ ] Verify dates shown

### No Tickets
- [ ] New user sends "My tickets"
- [ ] Receive "No tickets" message
- [ ] Receive helpful suggestions

### QR Code Access
- [ ] Send ticket code
- [ ] Receive QR code image
- [ ] Verify QR code scannable

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 6. Share Ticket ✅

### Share Flow
- [ ] Send "Share ticket"
- [ ] Receive list of tickets
- [ ] Send "1" to select ticket
- [ ] Receive prompt for recipient phone
- [ ] Send "+2348012345678"
- [ ] Receive transfer confirmation
- [ ] Verify recipient receives ticket
- [ ] Verify recipient receives QR code

### Validation
- [ ] Try invalid phone format → Error
- [ ] Try sharing to self → Error
- [ ] Try sharing invalid ticket → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 7. Request Refund ✅

### Refund Flow
- [ ] Send "Request refund"
- [ ] Receive list of bookings
- [ ] Send "1" to select booking
- [ ] Receive refund confirmation prompt
- [ ] Send "Yes" to confirm
- [ ] Receive refund processed message
- [ ] Verify refund amount shown
- [ ] Verify tickets cancelled

### Cancel Refund
- [ ] Start refund flow
- [ ] Send "No" at confirmation
- [ ] Verify booking remains active

### Validation
- [ ] Try refunding past event → Error
- [ ] Try refunding cancelled booking → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 8. Manage Event (Organizer) ✅

### View Events
- [ ] Send "Manage event"
- [ ] Receive list of organizer's events
- [ ] Verify stats shown (tickets sold, revenue)
- [ ] Verify management commands listed

### No Events
- [ ] New organizer sends "Manage event"
- [ ] Receive "No events" message
- [ ] Receive suggestion to create event

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 9. Event Statistics ✅

### View Stats
- [ ] Send "Stats 1"
- [ ] Receive detailed statistics
- [ ] Verify tickets sold/available
- [ ] Verify revenue total
- [ ] Verify bookings breakdown
- [ ] Verify check-in count
- [ ] Verify days until event

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 10. Broadcast Messages ✅

### Broadcast Flow
- [ ] Send "Broadcast 1"
- [ ] Receive prompt for message
- [ ] Send "Event update: Gates open at 7 PM"
- [ ] Receive delivery confirmation
- [ ] Verify delivery count shown
- [ ] Verify attendees receive message

### Cancel Broadcast
- [ ] Start broadcast
- [ ] Send "Cancel"
- [ ] Verify broadcast aborted

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 11. Analytics Dashboard ✅

### View Analytics
- [ ] Send "Analytics"
- [ ] Receive 30-day overview
- [ ] Verify total events
- [ ] Verify total bookings
- [ ] Verify total revenue
- [ ] Verify total tickets
- [ ] Verify top 3 events shown

### No Data
- [ ] New organizer sends "Analytics"
- [ ] Receive zeros for all metrics
- [ ] Receive helpful message

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 12. Download Reports ✅

### Generate Report
- [ ] Send "Download report"
- [ ] Receive "Generating..." message
- [ ] Receive report ready confirmation
- [ ] Verify report delivery method

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 13. Event Editing ✅

### Edit Flow
- [ ] Send "Edit 1"
- [ ] Receive editable fields (1-8)
- [ ] Send "3" (Date & Time)
- [ ] Receive current value
- [ ] Send "2026-04-15 19:00"
- [ ] Receive update confirmation
- [ ] Verify attendees notified

### Validation
- [ ] Try past date → Error
- [ ] Try capacity < tickets sold → Error
- [ ] Try invalid format → Error

### Edit Different Fields
- [ ] Edit title
- [ ] Edit description
- [ ] Edit location
- [ ] Edit capacity
- [ ] Edit price
- [ ] Edit category

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 14. Check-in System ✅

### Check-in Flow
- [ ] Send "checkin GRV-ABC123"
- [ ] Receive success message
- [ ] Verify attendee name shown
- [ ] Verify check-in time shown

### Validation
- [ ] Try invalid ticket code → Error
- [ ] Try already checked-in ticket → Error
- [ ] Try cancelled ticket → Error

### Anonymous Events
- [ ] Send "checkin GRV-ABC123 CODE123"
- [ ] Verify entry code validated
- [ ] Try wrong entry code → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 15. Multi-tier Tickets ✅

### View Tiers
- [ ] View event with tiers
- [ ] Verify tier options shown
- [ ] Verify tier prices
- [ ] Verify tier capacity
- [ ] Verify tier descriptions

### Book Tier
- [ ] Send "Book 1 2" (tier 1, qty 2)
- [ ] Verify tier price used
- [ ] Verify total calculated correctly
- [ ] Complete payment
- [ ] Receive tickets

### Sold-out Tier
- [ ] Try booking sold-out tier → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 16. Promo Codes ✅

### Apply Code
- [ ] Select event
- [ ] Send "promo SUMMER20"
- [ ] Receive code validation
- [ ] Verify discount shown
- [ ] Send "Book 2"
- [ ] Verify discount applied
- [ ] Verify final amount correct

### Validation
- [ ] Try invalid code → Error
- [ ] Try expired code → Error
- [ ] Try code at max uses → Error
- [ ] Try code with insufficient tickets → Error

### Discount Types
- [ ] Test percentage discount
- [ ] Test fixed amount discount
- [ ] Test max discount cap

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 17. AI Recommendations ✅

### Get Recommendations
- [ ] Send "Recommend"
- [ ] Receive 5 personalized events
- [ ] Verify based on history (if any)
- [ ] Verify categories matched
- [ ] Verify price range appropriate

### New User
- [ ] New user sends "Recommend"
- [ ] Receive popular events
- [ ] Verify sorted by popularity

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 18. Social Sharing ✅

### Share Event
- [ ] Select event
- [ ] Send "Share"
- [ ] Receive formatted share message
- [ ] Verify event details included
- [ ] Receive platform links
- [ ] Verify WhatsApp link
- [ ] Verify Twitter link
- [ ] Verify Facebook link
- [ ] Verify referral code included

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## 19. Gift Tickets ✅

### Gift Flow
- [ ] Select event
- [ ] Send "Gift ticket"
- [ ] Receive quantity prompt
- [ ] Send "2"
- [ ] Receive recipient phone prompt
- [ ] Send "08012345678"
- [ ] Receive message prompt
- [ ] Send "Happy Birthday! 🎉"
- [ ] Receive payment summary
- [ ] Complete payment
- [ ] Receive delivery confirmation

### Recipient Experience
- [ ] Recipient receives gift notification
- [ ] Verify sender name shown
- [ ] Verify gift message shown
- [ ] Verify event details shown
- [ ] Recipient receives QR codes (2x)

### Gift History
- [ ] Send "My gifts"
- [ ] Verify sent gifts shown
- [ ] Send "Gifts received"
- [ ] Verify received gifts shown

### Validation
- [ ] Try gifting to self → Error
- [ ] Try invalid phone → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## Error Handling Tests ✅

### General Errors
- [ ] Send gibberish → Helpful error message
- [ ] Send command in wrong context → Guidance
- [ ] Session expires → Clear message
- [ ] Network timeout → Retry message

### Payment Errors
- [ ] Payment fails → Error message
- [ ] Payment timeout → Guidance
- [ ] Invalid payment method → Error

### Booking Errors
- [ ] Sold-out event → Clear message
- [ ] Expired booking → Notification
- [ ] Insufficient capacity → Error

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## Performance Tests ✅

### Response Time
- [ ] All responses < 2 seconds
- [ ] Image delivery < 5 seconds
- [ ] Payment link generation < 3 seconds

### Concurrent Users
- [ ] 10 users booking simultaneously
- [ ] 50 users browsing events
- [ ] 100 messages per minute

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete | ❌ Failed

---

## Summary

### Test Results
- Total Features: 19
- Features Tested: __
- Features Passed: __
- Features Failed: __
- Issues Found: __

### Critical Issues
1. 
2. 
3. 

### Minor Issues
1. 
2. 
3. 

### Recommendations
1. 
2. 
3. 

### Sign-off
- [ ] All critical features working
- [ ] All tests documented
- [ ] Issues logged
- [ ] Ready for production

**Tester:** _______________
**Date:** _______________
**Signature:** _______________

---

**Testing Status:** 🧪 Ready to Begin
