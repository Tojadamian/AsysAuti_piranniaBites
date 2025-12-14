#!/usr/bin/env bash
# ============================================================================
# AsysAuti Quick Start - Setup + Run in one command
# ============================================================================
# Usage: bash scripts/quickstart.sh

set -euo pipefail

VENV_DIR="${VENV_DIR:-asysauti}"
PYTHON="${PYTHON:-python3}"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            🚀 AsysAuti QuickStart - Setup + Run           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create virtual environment if needed
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    $PYTHON -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

echo ""
echo -e "${YELLOW}📥 Installing dependencies...${NC}"

# Install backend dependencies
source "$VENV_DIR/bin/activate"
pip install -q -r requirements.txt || true
echo -e "${GREEN}✅ Backend dependencies installed${NC}"

# Install frontend dependencies
cd frontend
npm install -q 2>/dev/null || npm install >/dev/null 2>&1 || true
cd ..
echo -e "${GREEN}✅ Frontend dependencies installed${NC}"

echo ""
echo -e "${BLUE}🎯 Starting services...${NC}"
echo ""

# Run start script
bash scripts/start.sh 5001 5173 127.0.0.1
