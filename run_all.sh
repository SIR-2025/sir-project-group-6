#!/bin/bash

echo "======================================"
echo "Starting full Oli-4 system..."
echo "Using local Python venv"
echo "======================================"

# ===== DETERMINE ROOT DIR =====
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/venv/bin/python"
VENV_ACTIVATE="$ROOT_DIR/venv/bin/activate"

# ===== CHECK VENV =====
if [ ! -f "$VENV_PY" ]; then
    echo "[ERROR] venv not found at $VENV_PY"
    echo "Please run install.py or create a venv first:"
    echo "    python3 -m venv venv"
    echo "    source venv/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

# ===== STEP 1: START REDIS =====
echo "[1/3] Starting Redis server..."
redis-server "$ROOT_DIR/conf/redis/redis.conf" &
REDIS_PID=$!
echo "Redis PID: $REDIS_PID"

# ===== STEP 2: START GESTURE API =====
echo "[2/3] Starting Gesture API (local venv)..."

(
    source "$VENV_ACTIVATE"
    cd "$ROOT_DIR"
    python run_GestureAPI.py
) &

GESTURE_PID=$!
echo "Gesture API PID: $GESTURE_PID"

# ===== WAIT =====
echo
echo "Waiting 25 seconds for Redis and GestureAPI to fully start..."
sleep 25
echo "Continuing..."

# ===== STEP 3: START main.py =====
echo "[3/3] Starting main.py (local venv)..."

source "$VENV_ACTIVATE"
cd "$ROOT_DIR/oli-4"
python main.py
