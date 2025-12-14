@echo off
REM ============================================================================
REM AsysAuti Quick Start for Windows
REM ============================================================================
REM Usage: double-click or run: start.bat

setlocal enabledelayedexpansion

set VENV_DIR=asysauti
set BACKEND_PORT=5001
set FRONTEND_PORT=5173
set HOST=127.0.0.1

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           AsysAuti - Full Stack Developer Mode            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
    echo Virtual environment created
)

REM Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt 2>nul || pip install -r requirements.txt

echo.
echo Installing frontend dependencies...
cd frontend
npm install --quiet 2>nul || npm install
cd ..

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                   Starting Services                        ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Start backend in new window
echo Starting Backend (port %BACKEND_PORT%)...
start "AsysAuti Backend" cmd /k "python -c "from backend.web.app_factory import create_app; app=create_app(); app.run(host='%HOST%', port=%BACKEND_PORT%, debug=True)"

REM Wait for backend to start
timeout /t 2 /nobreak

REM Start frontend in new window
echo Starting Frontend (port %FRONTEND_PORT%)...
start "AsysAuti Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    Services Started                        ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo.
echo Close this window or press Ctrl+C to stop services.
echo.

pause

endlocal
