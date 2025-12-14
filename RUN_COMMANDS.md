# 🚀 AsysAuti - Run Commands Reference

## QUICK START - ONE COMMAND TO RUN EVERYTHING

```bash
# Method 1: Using Make (RECOMMENDED)
make

# Method 2: Using Make with full name
make all
make dev
make start
make run

# Method 3: Using QuickStart script (setup + run)
bash scripts/quickstart.sh
```

**Result:** Backend on port 5001 + Frontend on port 5173 in parallel! 🎉

---

## 📖 Available Make Commands

### 🎯 Main Commands

| Command | What it does | Output |
|---------|------------|--------|
| `make` | **RUN EVERYTHING** (backend + frontend) | Both services ready |
| `make all` | Same as `make` | Both services ready |
| `make dev` | Same as `make` | Both services ready |
| `make start` | Same as `make` | Both services ready |
| `make install` | Install all dependencies | Dependencies ready |
| `make setup` | Full setup (venv + install) | Everything ready |

### 🔧 Backend Commands

| Command | What it does | Port |
|---------|------------|------|
| `make backend` | Run backend only | 5001 |
| `make backend-debug` | Backend with debug logging | 5001 |
| `make backend-run` | Backend with app.py | 5000 |
| `make backend-deps` | Install backend dependencies only | - |

### 🎨 Frontend Commands

| Command | What it does | Port |
|---------|------------|------|
| `make frontend` | Run frontend only | 5173 |
| `make frontend-build` | Build for production | - |
| `make frontend-deps` | Install frontend dependencies only | - |

### 🛠️ Utility Commands

| Command | What it does |
|---------|------------|
| `make stop` | Stop all running services |
| `make status` | Check port status |
| `make clean` | Clean temporary files |
| `make test` | Run Python tests |
| `make lint` | Lint Python code |
| `make help` | Show all available commands |
| `make info` | Show environment info |

---

## 🎯 Customize Ports & Host

```bash
# Run backend on different port
make start BACKEND_PORT=8000

# Run frontend on different port
make start FRONTEND_PORT=3000

# Run on all network interfaces (0.0.0.0)
make start HOST=0.0.0.0

# Combine all
make start BACKEND_PORT=8000 FRONTEND_PORT=3000 HOST=0.0.0.0
```

---

## 🏃 Script-based Commands

### QuickStart (Setup + Run Everything)
```bash
bash scripts/quickstart.sh
```
✅ Creates venv if needed
✅ Installs dependencies
✅ Starts both services

### Start (Run Services Only)
```bash
bash scripts/start.sh [BACKEND_PORT] [FRONTEND_PORT] [HOST]

# Examples:
bash scripts/start.sh              # Default: 5001, 5173, 127.0.0.1
bash scripts/start.sh 5001 5173    # Custom ports
bash scripts/start.sh 5001 5173 0.0.0.0  # All interfaces
```

### Stop (Stop All Services)
```bash
bash scripts/stop.sh
# or
make stop
```

### Production (For Deployment)
```bash
bash scripts/prod.sh [PORT]

# Examples:
bash scripts/prod.sh              # Default: port 5000
bash scripts/prod.sh 8000         # Custom port
```

### Test (Run Tests)
```bash
bash scripts/test.sh
# or
make test
```

---

## 📋 Development Workflow

### First Time Setup
```bash
# One-time setup
make setup

# Or with QuickStart (includes setup)
bash scripts/quickstart.sh
```

### Daily Development
```bash
# Start everything
make

# Or
bash scripts/start.sh

# Or QuickStart every time
bash scripts/quickstart.sh
```

### Stop Services
```bash
# When done
make stop

# Or use Ctrl+C in terminal running services
```

---

## 🔧 Advanced Usage

### Check Port Status
```bash
make status

# Shows which services are running
```

### Backend Only (Separate Terminals)

Terminal 1 - Backend:
```bash
make backend
```

Terminal 2 - Frontend:
```bash
make frontend
```

### Backend with Debug Mode
```bash
make backend-debug

# Shows detailed logging
export LOG_LEVEL=DEBUG
make backend
```

### Run Tests
```bash
make test

# Or
bash scripts/test.sh
```

### Lint Code
```bash
make lint
```

### Build Frontend for Production
```bash
make frontend-build

# Creates optimized build in frontend/dist/
```

---

## 🔍 Service Endpoints

When everything is running:

| Service | URL | Purpose |
|---------|-----|---------|
| **Backend** | http://127.0.0.1:5001 | API Server |
| **API Health** | http://127.0.0.1:5001/ | Health check |
| **API Data** | http://127.0.0.1:5001/data_dir | Data directory |
| **Frontend** | http://127.0.0.1:5173 | Web UI |

---

## ⚙️ Configuration

### Environment Variables

```bash
# Set backend port
export BACKEND_PORT=5001

# Set frontend port
export FRONTEND_PORT=5173

# Set host
export HOST=127.0.0.1

# Set virtual env dir
export VENV_DIR=asysauti

# Set Python executable
export PYTHON=python3
```

### .env File Configuration

```bash
# Copy example
cp .env.production.example .env

# Edit with your settings
nano .env
```

See `.env.production.example` for available options.

---

## 📊 Ports Reference

| Service | Default Port | Can be Changed |
|---------|-------------|----------------|
| Backend (Dev) | 5001 | Yes - `BACKEND_PORT=xxxx` |
| Frontend (Dev) | 5173 | Yes - `FRONTEND_PORT=xxxx` |
| Backend (Prod) | 5000 | Yes - `scripts/prod.sh 5000` |

---

## 🆘 Troubleshooting

### "Port already in use"

```bash
# Check what's on the port
make status

# Kill specific port (macOS/Linux)
lsof -i :5001 -sTCP:LISTEN -P -n | awk 'NR!=1 {print $2}' | xargs kill -9

# Or stop all
make stop
```

### Virtual environment issues

```bash
# Clean and recreate
rm -rf asysauti
make setup
make
```

### Dependencies not installing

```bash
# Clean and reinstall
make clean-venv
make install
```

### Frontend not showing changes

```bash
# Clear node_modules and reinstall
make clean-node
make frontend
```

---

## 🐛 Debugging

### Backend with Debug Logs
```bash
make backend-debug

# Or set log level
export LOG_LEVEL=DEBUG
make backend
```

### Check What's Running
```bash
make status

# Or use system tools
ps aux | grep python
ps aux | grep node
```

### Test API Endpoints
```bash
# Health check
curl http://127.0.0.1:5001/

# Data directory
curl http://127.0.0.1:5001/data_dir

# With timing
curl -w "\nTime: %{time_total}s\n" http://127.0.0.1:5001/
```

---

## 📈 Performance Monitoring

### Monitor Services
```bash
# Check if services are responding
watch -n 2 'curl -s http://127.0.0.1:5001/ && echo "Backend OK"'

# Monitor processes
top -o %CPU -o %MEM
```

### Check Logs
```bash
# Backend logs appear in terminal running 'make backend'
# Frontend logs appear in terminal running 'make frontend'
```

---

## 🚀 Production Deployment

### Single Server Deployment
```bash
# Install and start
bash scripts/quickstart.sh

# Or
make setup
bash scripts/prod.sh 5000
```

### Docker Deployment
```bash
# Build image (assuming Dockerfile exists)
docker build -t asysauti .

# Run container
docker run -p 5000:5000 -p 3000:3000 asysauti
```

---

## 📝 Common Commands Cheatsheet

```bash
# Setup everything (first time only)
make setup

# Run everything (daily development)
make

# Stop services
make stop

# Backend only
make backend

# Frontend only
make frontend

# Run tests
make test

# Clean files
make clean

# Help
make help

# Quick info
make info
```

---

## ✅ Verification

After running services, you should see:

```
✅ Backend running at http://127.0.0.1:5001
✅ Frontend running at http://127.0.0.1:5173
```

Test them:
```bash
# Terminal 1 - Check backend
curl http://127.0.0.1:5001/

# Terminal 2 - Open frontend
open http://127.0.0.1:5173
```

---

**Last Updated:** December 14, 2025
**Status:** Production Ready ✅
**Fully Optimized:** Yes ✅
