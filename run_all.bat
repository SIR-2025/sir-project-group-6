@echo off
echo ======================================
echo Starting full Oli-4 system...
echo ======================================

REM ====== STEP 1: START REDIS SERVER ======
echo [1/3] Starting Redis server...
start "Redis" cmd /k ".\conf\redis\redis-server.exe .\conf\redis\redis.conf"

REM ====== STEP 2: START GESTURE API IN env_sic ======
echo [2/3] Starting Gesture API (env_sic)...
start "GestureAPI" cmd /k "call C:\Miniforge3\Scripts\activate.bat C:\Miniforge3\envs\env_sic && cd oli-4\config && python run_GestureAPI.py"

REM ====== WAIT FOR SERVICES TO START ======
echo.
echo Waiting 25 seconds for Redis and GestureAPI to fully start...
timeout /t 25 /nobreak >nul
echo Continuing...

REM ====== STEP 3: START main.py IN env_sic ======
echo [3/3] Starting main.py (env_sic)...
call C:\Miniforge3\Scripts\activate.bat C:\Miniforge3\envs\env_sic
cd oli-4
python main.py

pause
