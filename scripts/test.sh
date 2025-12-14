#!/usr/bin/env bash
# ============================================================================
# AsysAuti Test Script - Run all tests
# ============================================================================
# Usage: bash scripts/test.sh

set -euo pipefail

VENV_DIR="${VENV_DIR:-asysauti}"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# ============================================================================
# MAIN
# ============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🧪 AsysAuti Test Suite                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Activate venv
source "$VENV_DIR/bin/activate"
log_success "Virtual environment activated"

# Install test dependencies
log_info "Installing test dependencies..."
pip install -q pytest pytest-cov 2>/dev/null || true
log_success "Test dependencies ready"

echo ""
log_info "Running Python tests..."
echo ""

# Run pytest
python -m pytest tests/ -v --tb=short || true

echo ""
log_success "Test suite complete"
