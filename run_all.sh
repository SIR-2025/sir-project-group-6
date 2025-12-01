#!/bin/bash

echo "======================================"
echo "Starting full Oli-4 system (macOS)..."
echo "======================================"

# ===== STEP 1: START REDIS SERVER =====
echo "[1/3] Starting Redis server..."
# Zorg dat Redis via Homebrew staat: brew install redis
redis-server ./conf/redis/redis.conf &
REDIS_PID=$!
echo "Redis PID: $REDIS_PID"

# ===== STEP 2: START GESTURE API =====
echo "[2/3] Starting Gesture API (env_sic)..."

# Activeer venv en start Gesture API in background
(
    source venv/bin/activate
    cd oli-4/config
    python run_GestureAPI.py
) &

GESTURE_PID=$!
echo "Gesture API PID: $GESTURE_PID"

echo
echo "Waiting 25 seconds for Redis and GestureAPI to fully start..."
sleep 25
echo "Continuing..."

# ===== STEP 3: START main.py =====
echo "[3/3] Starting main.py (env_sic)..."

source venv/bin/activate
cd oli-4
python main.py