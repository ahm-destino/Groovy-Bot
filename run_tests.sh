#!/bin/bash

# Grooovy WhatsApp Bot - Test Runner Script

echo "🧪 Grooovy WhatsApp Bot - Test Suite"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "Install with: pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

echo -e "${GREEN}✅ pytest found${NC}"
echo ""

# Run tests based on argument
case "$1" in
    "all")
        echo "Running all tests..."
        pytest -v
        ;;
    "coverage")
        echo "Running tests with coverage..."
        pytest --cov=app --cov-report=html --cov-report=term
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "unit")
        echo "Running unit tests..."
        pytest tests/test_*.py -v
        ;;
    "registration")
        echo "Running user registration tests..."
        pytest tests/test_user_registration.py -v
        ;;
    "bookings")
        echo "Running booking tests..."
        pytest tests/test_bookings.py -v
        ;;
    "gifts")
        echo "Running gift tickets tests..."
        pytest tests/test_gift_tickets.py -v
        ;;
    "quick")
        echo "Running quick smoke tests..."
        pytest -x --tb=short
        ;;
    "watch")
        echo "Running tests in watch mode..."
        pytest-watch
        ;;
    *)
        echo "Usage: ./run_tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  all          - Run all tests"
        echo "  coverage     - Run tests with coverage report"
        echo "  unit         - Run unit tests only"
        echo "  registration - Run user registration tests"
        echo "  bookings     - Run booking tests"
        echo "  gifts        - Run gift tickets tests"
        echo "  quick        - Run quick smoke tests"
        echo "  watch        - Run tests in watch mode"
        echo ""
        echo "Example: ./run_tests.sh coverage"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
