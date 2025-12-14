# ============================================================================
# AsysAuti Makefile - Development & Production Commands
# ============================================================================
# Single command to run everything: make start OR make dev OR make all

PYTHON?=python3
VENV_DIR?=asysauti
VENV_BIN=$(VENV_DIR)/bin
VENV_PY=$(VENV_BIN)/python
VENV_PIP=$(VENV_BIN)/pip
SHELL:=/bin/bash
.SHELLFLAGS:=--noprofile --norc -eo pipefail -O globstar -c

# Ports
BACKEND_PORT?=5001
FRONTEND_PORT?=5173
HOST?=127.0.0.1

# Colors for output
BLUE:=\033[0;34m
GREEN:=\033[0;32m
YELLOW:=\033[1;33m
RED:=\033[0;31m
NC:=\033[0m

# ============================================================================
# MAIN TARGETS - USE THESE
# ============================================================================

.PHONY: all dev start run frontend-dev install help

## all, dev, start, run - Run backend (5001) + frontend (5173) in parallel
all dev start run: install
	@echo "$(BLUE)🚀 Starting AsysAuti (Backend port $(BACKEND_PORT), Frontend port $(FRONTEND_PORT))$(NC)"
	@bash scripts/start.sh $(BACKEND_PORT) $(FRONTEND_PORT) $(HOST)

## install - Install all dependencies (backend + frontend)
install: venv backend-deps frontend-deps
	@echo "$(GREEN)✅ All dependencies installed$(NC)"

## setup - Full setup (venv + install)
setup: venv install
	@echo "$(GREEN)✅ Setup complete$(NC)"

# ============================================================================
# BACKEND TARGETS
# ============================================================================

.PHONY: backend backend-deps backend-run backend-debug

## backend - Run only backend on port 5001
backend: backend-deps
	@echo "$(BLUE)🔧 Starting Backend (port $(BACKEND_PORT))$(NC)"
	@cd $(VENV_BIN) && ./activate && $(VENV_PY) -c \
		"from backend.web.app_factory import create_app; \
		app=create_app(); \
		app.run(host='$(HOST)', port=$(BACKEND_PORT), debug=True)"

## backend-deps - Install backend dependencies
backend-deps: venv
	@echo "$(YELLOW)📦 Installing backend dependencies...$(NC)"
	@$(VENV_PIP) install -q -r requirements.txt || true
	@echo "$(GREEN)✅ Backend dependencies ready$(NC)"

## backend-run - Run backend directly with app.py
backend-run: venv backend-deps
	@echo "$(BLUE)🔧 Starting Backend with app.py$(NC)"
	@source $(VENV_BIN)/activate && \
		export FLASK_ENV=development && \
		$(VENV_PY) app.py

## backend-debug - Run backend with debug logging
backend-debug: venv backend-deps
	@echo "$(BLUE)🔧 Starting Backend (DEBUG MODE)$(NC)"
	@source $(VENV_BIN)/activate && \
		export LOG_LEVEL=DEBUG && \
		export FLASK_ENV=development && \
		$(VENV_PY) -c \
			"from backend.web.app_factory import create_app; \
			app=create_app(); \
			app.run(host='$(HOST)', port=$(BACKEND_PORT), debug=True)"

# ============================================================================
# FRONTEND TARGETS
# ============================================================================

.PHONY: frontend frontend-deps frontend-dev frontend-build

## frontend - Run only frontend on port 5173
frontend: frontend-deps
	@echo "$(BLUE)🎨 Starting Frontend (port $(FRONTEND_PORT))$(NC)"
	@cd frontend && npm run dev

## frontend-deps - Install frontend dependencies
frontend-deps:
	@echo "$(YELLOW)📦 Installing frontend dependencies...$(NC)"
	@cd frontend && npm install -q 2>/dev/null || npm install
	@echo "$(GREEN)✅ Frontend dependencies ready$(NC)"

## frontend-dev - Alias for frontend
frontend-dev: frontend

## frontend-build - Build frontend for production
frontend-build: frontend-deps
	@echo "$(YELLOW)📦 Building frontend...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)✅ Frontend built$(NC)"

# ============================================================================
# VIRTUAL ENVIRONMENT
# ============================================================================

.PHONY: venv

## venv - Create or verify virtual environment
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(YELLOW)🔨 Creating virtual environment at $(VENV_DIR)...$(NC)"; \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "$(GREEN)✅ Virtual environment created$(NC)"; \
	else \
		echo "$(GREEN)✅ Virtual environment exists at $(VENV_DIR)$(NC)"; \
	fi

# ============================================================================
# UTILITY TARGETS
# ============================================================================

.PHONY: clean clean-venv clean-node stop status test

## stop - Stop all running processes started by make
stop:
	@echo "$(YELLOW)🛑 Stopping all processes...$(NC)"
	@bash scripts/stop.sh

## clean - Clean all temporary files and caches
clean:
	@echo "$(YELLOW)🧹 Cleaning temporary files...$(NC)"
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@cd frontend && npm run build:clean 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

## clean-venv - Remove virtual environment
clean-venv:
	@echo "$(YELLOW)🗑️  Removing virtual environment...$(NC)"
	@rm -rf $(VENV_DIR)
	@echo "$(GREEN)✅ Virtual environment removed$(NC)"

## clean-node - Remove node_modules and package-lock
clean-node:
	@echo "$(YELLOW)🗑️  Removing node_modules...$(NC)"
	@rm -rf frontend/node_modules frontend/package-lock.json
	@echo "$(GREEN)✅ Node modules removed$(NC)"

## status - Show status of ports
status:
	@echo "$(BLUE)📊 Checking port status...$(NC)"
	@if command -v lsof >/dev/null 2>&1; then \
		echo "Backend ($(BACKEND_PORT)):"; \
		lsof -i :$(BACKEND_PORT) -P -n 2>/dev/null | tail -1 || echo "  ✅ Available"; \
		echo "Frontend ($(FRONTEND_PORT)):"; \
		lsof -i :$(FRONTEND_PORT) -P -n 2>/dev/null | tail -1 || echo "  ✅ Available"; \
	else \
		echo "$(YELLOW)⚠️  lsof not available on this system$(NC)"; \
	fi

## test - Run tests
test: venv backend-deps
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@source $(VENV_BIN)/activate && $(VENV_PY) -m pytest tests/ -v

## lint - Run Python linting
lint: venv backend-deps
	@echo "$(BLUE)🔍 Linting Python code...$(NC)"
	@source $(VENV_BIN)/activate && $(VENV_PY) -m flake8 backend/ --max-line-length=100 || true

# ============================================================================
# HELP & INFO
# ============================================================================

.PHONY: help info

## help - Show this help message
help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║          AsysAuti Development - Make Commands                  ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 START HERE:$(NC)"
	@echo "  make                          Run everything (backend + frontend)"
	@echo "  make all                      Same as above"
	@echo "  make dev                      Same as above"
	@echo "  make start                    Same as above"
	@echo ""
	@echo "$(GREEN)🔧 BACKEND:$(NC)"
	@echo "  make backend                  Run backend only (port $(BACKEND_PORT))"
	@echo "  make backend-debug            Run backend with debug logging"
	@echo "  make backend-run              Run backend with app.py"
	@echo ""
	@echo "$(GREEN)🎨 FRONTEND:$(NC)"
	@echo "  make frontend                 Run frontend only (port $(FRONTEND_PORT))"
	@echo "  make frontend-build           Build frontend for production"
	@echo ""
	@echo "$(GREEN)📦 SETUP:$(NC)"
	@echo "  make install                  Install all dependencies"
	@echo "  make setup                    Full setup (venv + install)"
	@echo "  make venv                     Create virtual environment"
	@echo ""
	@echo "$(GREEN)🛠️  TOOLS:$(NC)"
	@echo "  make stop                     Stop all running processes"
	@echo "  make status                   Check port status"
	@echo "  make clean                    Clean temporary files"
	@echo "  make test                     Run tests"
	@echo "  make lint                     Lint Python code"
	@echo ""
	@echo "$(YELLOW)📝 CONFIGURATION:$(NC)"
	@echo "  BACKEND_PORT=$(BACKEND_PORT)           Change with: make start BACKEND_PORT=8000"
	@echo "  FRONTEND_PORT=$(FRONTEND_PORT)          Change with: make start FRONTEND_PORT=3000"
	@echo "  HOST=$(HOST)                Change with: make start HOST=0.0.0.0"
	@echo ""
	@echo "$(BLUE)📚 Full documentation in RUN_COMMANDS.md$(NC)"
	@echo ""

## info - Show environment info
info:
	@echo "$(BLUE)ℹ️  Environment Information:$(NC)"
	@echo "  Python:          $$($(PYTHON) --version 2>&1)"
	@echo "  Node/npm:        $$(npm --version 2>/dev/null || echo 'Not installed')"
	@echo "  Virtual env:     $(VENV_DIR)"
	@echo "  Backend port:    $(BACKEND_PORT)"
	@echo "  Frontend port:   $(FRONTEND_PORT)"
	@echo "  Host:            $(HOST)"

# Default target - run everything
.DEFAULT_GOAL:=start
