# Quick Test Reference

## ✅ Python & Testing Setup Complete!

All dependencies are installed and tests are configured. You're ready to test!

---

## 🚀 Running Tests

### Option 1: Unit Tests (No Database Required)

These tests validate logic without needing PostgreSQL:

```bash
TESTING=1 python3 -m pytest tests/test_user_registration.py::test_registration_flow_validation tests/test_user_registration.py::test_email_validation -v
```

**Result:** ✅ 2 PASSED

### Option 2: Full Test Suite (Requires Database)

To run all 19 tests, you need PostgreSQL running:

```bash
# Start database
docker-compose up -d postgres

# Run all tests
TESTING=1 python3 -m pytest tests/ -v

# Run with coverage
TESTING=1 python3 -m pytest tests/ -v --cov=app --cov-report=html
```

### Option 3: Manual Testing (Recommended)

Test via WhatsApp using the comprehensive checklist:

```bash
# View the checklist
cat MANUAL_TESTING_CHECKLIST.md

# Or open in your editor
open MANUAL_TESTING_CHECKLIST.md
```

---

## 📊 Test Coverage

### Automated Tests (19 total)
- **User Registration:** 7 tests
- **Bookings:** 6 tests  
- **Gift Tickets:** 5 tests
- **Email Validation:** 1 test

### Manual Testing Checklist
- **19 Features** across 4 categories
- **Core Features:** 6
- **Organizer Features:** 7
- **Advanced Features:** 5
- **Gift Features:** 1

---

## 🔧 What Was Installed

```bash
# Core testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==7.0.0

# Database
sqlalchemy==2.0.25
asyncpg==0.29.0
greenlet==3.2.5

# All project dependencies from requirements.txt
```

---

## 📝 Test Files

- `tests/test_user_registration.py` - User registration tests
- `tests/test_bookings.py` - Booking system tests
- `tests/test_gift_tickets.py` - Gift tickets tests
- `tests/conftest.py` - Test configuration & fixtures
- `.env.test` - Test environment variables

---

## 🎯 Next Steps

### Immediate (No Database)
1. ✅ Run validation tests (already passing)
2. ✅ Review manual testing checklist
3. ✅ Start manual testing via WhatsApp

### With Database
1. Start PostgreSQL: `docker-compose up -d postgres`
2. Run full test suite: `TESTING=1 python3 -m pytest tests/ -v`
3. Fix any failing tests
4. Generate coverage report

### Production Ready
1. Complete all manual testing
2. Document any issues found
3. Fix critical bugs
4. Re-test problem areas
5. Sign off on testing

---

## 💡 Pro Tips

**Run specific test:**
```bash
TESTING=1 python3 -m pytest tests/test_user_registration.py::test_check_registration_status_new_user -v
```

**Run tests matching pattern:**
```bash
TESTING=1 python3 -m pytest tests/ -k "registration" -v
```

**Show print statements:**
```bash
TESTING=1 python3 -m pytest tests/ -v -s
```

**Stop on first failure:**
```bash
TESTING=1 python3 -m pytest tests/ -v -x
```

---

## 🐛 Troubleshooting

**"Connection refused" error:**
- PostgreSQL isn't running
- Start it: `docker-compose up -d postgres`

**"Module not found" error:**
- Missing dependency
- Install: `python3 -m pip install --user <package>`

**"Fixture not found" error:**
- Check `tests/conftest.py` has the fixture
- Ensure test file imports pytest

---

## ✅ Current Status

- ✅ Python 3.9.6 installed
- ✅ pip installed
- ✅ All dependencies installed
- ✅ Test environment configured
- ✅ 2 validation tests passing
- ⏳ Database tests pending (need PostgreSQL)
- ⏳ Manual testing pending

---

## 🎉 You're Ready!

Choose your testing approach:

1. **Quick validation:** Run the 2 passing tests
2. **Full automated:** Start database + run all 19 tests
3. **Comprehensive:** Manual testing via WhatsApp (2-3 hours)

**Recommended:** Start with manual testing while database setup is pending.

