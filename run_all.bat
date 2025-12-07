@echo off
echo ======================================
echo Starting full Oli-4 system...
echo Using local Python venv
echo ======================================

REM ====== DETERMINE PATHS ======
set ROOT_DIR=%~dp0
set VENV_ACTIVATE=%ROOT_DIR%venv\Scripts\activate.bat
set VENV_PY=%ROOT_DIR%venv\Scripts\python.exe

IF NOT EXIST "%VENV_PY%" (
    echo [ERROR] venv not found at "%VENV_PY%"
    echo Please run install.py or create a venv first:
    echo     python -m venv venv
    echo     venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

REM ====== STEP 1: START REDIS SERVER ======
echo [1/3] Starting Redis server...
start "Redis" cmd /k "%ROOT_DIR%conf\redis\redis-server.exe %ROOT_DIR%conf\redis\redis.conf"

REM ====== STEP 2: START GESTURE API IN LOCAL venv ======
echo [2/3] Starting Gesture API (local venv)...
start "GestureAPI" cmd /k "call "%VENV_ACTIVATE%" && cd /d "%ROOT_DIR%" && python run_GestureAPI.py"

REM ====== WAIT FOR SERVICES TO START ======
echo.
echo Waiting 25 seconds for Redis and GestureAPI to fully start...
timeout /t 25 /nobreak >nul
echo Continuing...

REM ====== STEP 3: START main.py IN LOCAL venv ======
echo [3/3] Starting main.py (local venv)...
call "%VENV_ACTIVATE%"
cd /d "%ROOT_DIR%oli-4"
python main.py

pause
