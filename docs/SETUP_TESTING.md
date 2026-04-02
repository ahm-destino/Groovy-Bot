# Setting Up Testing Environment

## Issue: pip not found

You're seeing this error because Python/pip is not installed or not in your PATH.

---

## Solution 1: Use pip3 (Most Common on macOS)

```bash
# Try pip3 instead
pip3 --version

# If pip3 works, install test dependencies
pip3 install pytest pytest-asyncio pytest-cov

# Then run tests
./run_tests.sh all
```

---

## Solution 2: Install Python via Homebrew

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Verify installation
python3 --version
pip3 --version

# Install test dependencies
pip3 install pytest pytest-asyncio pytest-cov

# Run tests
./run_tests.sh all
```

---

## Solution 3: Use Python venv (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests
./run_tests.sh all

# When done, deactivate
deactivate
```

---

## Solution 4: Skip Automated Tests, Do Manual Testing

If you can't set up Python/pytest right now, you can proceed with manual testing via WhatsApp:

```bash
# View the manual testing checklist
cat MANUAL_TESTING_CHECKLIST.md

# Or open in your editor
open MANUAL_TESTING_CHECKLIST.md
```

### Manual Testing Steps:

1. **Set up WhatsApp Bot**
   - Configure WhatsApp Business API
   - Set webhook URL
   - Get test phone number

2. **Test Each Feature**
   - Follow MANUAL_TESTING_CHECKLIST.md
   - Test via WhatsApp messages
   - Check off each item
   - Document any issues

3. **Key Features to Test:**
   ```
   User: Hi                    # Registration
   User: Events in Lagos       # Discovery
   User: 1                     # Event details
   User: Book 2                # Booking
   User: My tickets            # View tickets
   User: Gift ticket           # Gift flow
   User: Manage event          # Organizer
   ```

---

## Quick Verification

### Check Python Installation
```bash
# Check if Python is installed
which python3
python3 --version

# Check if pip is available
which pip3
pip3 --version
```

### Check Project Dependencies
```bash
# View required packages
cat requirements.txt

# Check if virtual environment exists
ls -la venv/
```

---

## Recommended Approach

### For Development & Testing:

1. **Use Virtual Environment** (Best Practice)
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install pytest pytest-asyncio pytest-cov
   ```

2. **Run Automated Tests**
   ```bash
   ./run_tests.sh all
   ```

3. **Run Manual Tests**
   - Use WhatsApp to test features
   - Follow MANUAL_TESTING_CHECKLIST.md

---

## Alternative: Docker Testing

If you have Docker installed:

```bash
# Build test container
docker build -t grooovy-test -f Dockerfile.test .

# Run tests in container
docker run grooovy-test pytest

# Run with coverage
docker run grooovy-test pytest --cov=app
```

---

## What to Do Right Now

### Option A: Quick Setup (5 minutes)
```bash
# Use pip3
pip3 install pytest pytest-asyncio pytest-cov

# Run tests
./run_tests.sh all
```

### Option B: Proper Setup (10 minutes)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests
./run_tests.sh all
```

### Option C: Manual Testing Only (Start Now)
```bash
# Skip automated tests
# Go straight to manual testing
open MANUAL_TESTING_CHECKLIST.md

# Test via WhatsApp
# Follow the checklist
```

---

## Common Issues & Fixes

### Issue: "command not found: pip"
**Fix:** Use `pip3` instead of `pip`

### Issue: "command not found: python"
**Fix:** Use `python3` instead of `python`

### Issue: "Permission denied"
**Fix:** Use `pip3 install --user` or use virtual environment

### Issue: "No module named pytest"
**Fix:** Install pytest: `pip3 install pytest`

---

## Next Steps

1. Choose one of the options above
2. Set up your environment
3. Run automated tests OR
4. Proceed with manual testing
5. Document results

---

## Need Help?

If you're still having issues:

1. **Check Python Installation:**
   ```bash
   python3 --version
   pip3 --version
   ```

2. **Check Project Structure:**
   ```bash
   ls -la
   cat requirements.txt
   ```

3. **Try Manual Testing:**
   - Skip automated tests for now
   - Test features via WhatsApp
   - Use MANUAL_TESTING_CHECKLIST.md

---

## Summary

**Problem:** pip not found
**Solution:** Use pip3 or install Python
**Quick Fix:** `pip3 install pytest pytest-asyncio pytest-cov`
**Alternative:** Manual testing via WhatsApp

**Status:** Ready to proceed with testing once Python/pip is set up! 🧪
