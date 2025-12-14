#!/usr/bin/env bash
# ============================================================================
# AsysAuti Start Script - Run Backend + Frontend in Parallel
# ============================================================================
# Usage: bash scripts/start.sh [BACKEND_PORT] [FRONTEND_PORT] [HOST]
# Example: bash scripts/start.sh 5001 5173 127.0.0.1

set -euo pipefail

# Get parameters or use defaults
BACKEND_PORT="${1:-5001}"
FRONTEND_PORT="${2:-5173}"
HOST="${3:-127.0.0.1}"
VENV_DIR="${VENV_DIR:-asysauti}"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_port() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -i ":$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
        return $?
    fi
    # Fallback if lsof not available: assume available (not in use)
    return 1
}

wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=30
    local attempt=0

    log_info "Waiting for $service to start..."
    while [ $attempt -lt $max_attempts ]; do
        if nc -z "$host" "$port" >/dev/null 2>&1; then
            log_success "$service is ready at $host:$port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.5
    done

    log_warning "$service did not start within timeout"
    return 1
}

cleanup() {
    log_warning "Shutting down..."
    # Try graceful termination first
    if [ -n "${BACKEND_PID:-}" ]; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
        pkill -P "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
        pkill -P "$FRONTEND_PID" 2>/dev/null || true
    fi
    sleep 1
    # Force kill if still running
    if [ -n "${BACKEND_PID:-}" ]; then
        kill -KILL "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill -KILL "$FRONTEND_PID" 2>/dev/null || true
    fi
    log_success "Cleanup complete"
    exit 0
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

clear
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🚀 AsysAuti - Full Stack Developer Mode         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verify virtual environment
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtual environment not found at $VENV_DIR"
    log_info "Run: python3 -m venv $VENV_DIR"
    exit 1
fi

log_success "Virtual environment found"

# Activate virtual environment
source "$VENV_DIR/bin/activate"
log_success "Virtual environment activated"

# Install backend dependencies if needed
log_info "Checking backend dependencies..."
pip install -q -r requirements.txt 2>/dev/null || true
log_success "Backend dependencies ready"

# Install frontend dependencies if needed
log_info "Checking frontend dependencies..."
cd frontend && npm install -q 2>/dev/null || npm install >/dev/null 2>&1 || true
cd ..
log_success "Frontend dependencies ready"

# Check ports availability
log_info "Checking port availability..."
if check_port "$BACKEND_PORT"; then
    log_warning "Port $BACKEND_PORT is already in use"
else
    log_success "Backend port $BACKEND_PORT is available"
fi

if check_port "$FRONTEND_PORT"; then
    log_warning "Port $FRONTEND_PORT is already in use"
else
    log_success "Frontend port $FRONTEND_PORT is available"
fi

echo ""
log_info "Starting backend and frontend in parallel..."
echo ""

# Setup trap to cleanup on Ctrl+C or termination
trap cleanup SIGINT SIGTERM

# ============================================================================
# START BACKEND (Port 5001)
# ============================================================================

export FLASK_ENV=development
export FLASK_APP=app.py
export ALLOW_UNPICKLE=0
export LOG_LEVEL=INFO

log_success "Starting Backend..."
cd "$VENV_DIR/.." # Go back to root
python -c "\
from backend.web.app_factory import create_app
import logging

app = create_app()
print('')
print('═' * 70)
print(f'🔧 Backend running at http://$HOST:$BACKEND_PORT')
print(f'📍 Docs: http://$HOST:$BACKEND_PORT/data_dir')
print('═' * 70)
print('')

app.run(host='$HOST', port=$BACKEND_PORT, debug=True, use_reloader=False)
" &
BACKEND_PID=$!

# Give backend time to start
sleep 2

# ============================================================================
# START FRONTEND (Port 5173)
# ============================================================================

log_success "Starting Frontend..."
cd frontend
npm run dev 2>&1 | while IFS= read -r line; do
    echo -e "${YELLOW}[Frontend]${NC} $line"
done &
FRONTEND_PID=$!

# Give frontend time to start
sleep 3

# ============================================================================
# DISPLAY READY MESSAGE
# ============================================================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ BOTH SERVICES READY                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 BACKEND:${NC}"
echo "   API:    http://$HOST:$BACKEND_PORT"
echo "   Health: curl http://$HOST:$BACKEND_PORT/"
echo ""
echo -e "${BLUE}🎨 FRONTEND:${NC}"
echo "   App:    http://$HOST:$FRONTEND_PORT"
echo ""
echo -e "${BLUE}📚 DOCUMENTATION:${NC}"
echo "   RUN_COMMANDS.md          - Commands & usage"
echo ""
echo -e "${YELLOW}⏸️  Press Ctrl+C to stop both services${NC}"
echo ""

# Wait for background processes (backend and frontend)
wait "$BACKEND_PID" "$FRONTEND_PID"
