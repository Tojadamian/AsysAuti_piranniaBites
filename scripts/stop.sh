#!/usr/bin/env bash
# ============================================================================
# AsysAuti Stop Script - Stop all running processes
# ============================================================================
# Usage: bash scripts/stop.sh OR make stop

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

# Kill process by port
kill_by_port() {
    local port=$1
    local name=$2
    
    if command -v lsof >/dev/null 2>&1; then
        local pids=$(lsof -i ":$port" -sTCP:LISTEN -P -n 2>/dev/null | tail -n +2 | awk '{print $2}')
        if [ -n "$pids" ]; then
            log_info "Stopping $name (port $port)..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            log_success "$name stopped"
        else
            log_warning "$name not running on port $port"
        fi
    else
        log_warning "lsof not available, trying generic approach..."
        pkill -f "port.*$port" 2>/dev/null || true
        pkill -f "5001" 2>/dev/null || true
        pkill -f "5173" 2>/dev/null || true
        log_success "Processes terminated"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 🛑 Stopping AsysAuti                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Kill processes
kill_by_port 5001 "Backend"
kill_by_port 5173 "Frontend"

# Also try to kill by process name
log_info "Cleaning up processes..."
pkill -f "flask" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

sleep 1

echo ""
log_success "All services stopped"
echo ""
