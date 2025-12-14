#!/usr/bin/env bash
# ============================================================================
# AsysAuti Production Start - Optimized for production deployment
# ============================================================================
# Usage: bash scripts/prod.sh [PORT]

set -euo pipefail

BACKEND_PORT="${1:-5000}"
HOST="${HOST:-0.0.0.0}"
VENV_DIR="${VENV_DIR:-asysauti}"
WORKERS="${WORKERS:-4}"

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
echo -e "${BLUE}║              🚀 AsysAuti Production Start                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Activate venv
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
log_success "Virtual environment activated"

# Install dependencies
log_info "Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null || true
log_success "Dependencies ready"

# Check for gunicorn
if ! command -v gunicorn &> /dev/null; then
    log_info "Installing gunicorn (production server)..."
    pip install -q gunicorn 2>/dev/null
fi

# Production environment
export FLASK_ENV=production
export FLASK_DEBUG=false
export LOG_LEVEL=WARNING
export ALLOW_UNPICKLE=0

echo ""
log_success "Starting production server (gunicorn)..."
echo ""
echo -e "${BLUE}🔍 Configuration:${NC}"
echo "   Workers:      $WORKERS"
echo "   Port:         $BACKEND_PORT"
echo "   Host:         $HOST"
echo "   Environment:  Production"
echo ""

# Start gunicorn
gunicorn \
    --workers $WORKERS \
    --worker-class sync \
    --bind "$HOST:$BACKEND_PORT" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    'backend.web.app_factory:create_app()'
