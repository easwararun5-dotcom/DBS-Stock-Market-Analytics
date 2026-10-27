#!/usr/bin/env bash
# ==============================================================================
# DBS Stock Market Analytics — Service Shutdown Script
# ==============================================================================
# Gracefully stops:
#   1. React/Vite frontend (port 5173)
#   2. FastAPI backend (port 8000)
#   3. Optionally stops TimescaleDB container when passed '--all'
#
# Usage:
#   ./stop.sh          # Stops backend & frontend servers
#   ./stop.sh --all    # Stops backend, frontend, and Docker container
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PID_DIR="$PROJECT_ROOT/.run"

echo "=========================================================="
echo " Stopping DBS Stock Market Analytics Services"
echo "=========================================================="

stop_pid_file() {
    local pid_file=$1
    local name=$2
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "[INFO] Stopping $name (PID: $pid)..."
            pkill -P "$pid" 2>/dev/null || true
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo "[INFO] $name stopped."
        fi
        rm -f "$pid_file" 2>/dev/null || true
    fi
}

stop_port() {
    local port=$1
    local name=$2
    local pids
    pids=$(lsof -ti :"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            local comm
            comm=$(ps -p "$pid" -o comm= 2>/dev/null || echo "process")
            echo "[INFO] Stopping $name on port $port ($comm, PID: $pid)..."
            pkill -P "$pid" 2>/dev/null || true
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
        echo "[INFO] Port $port is now free."
    fi
}

# 1. Stop recorded PIDs
stop_pid_file "$PID_DIR/frontend.pid" "Frontend"
stop_pid_file "$PID_DIR/backend.pid" "Backend"

# 2. Free ports in case orphaned
stop_port 5173 "Frontend"
stop_port 8000 "Backend"

# 3. Handle Docker if requested
if [ "$1" = "--all" ] || [ "$1" = "--docker" ]; then
    echo "[INFO] Stopping TimescaleDB Docker container..."
    if command -v docker >/dev/null 2>&1; then
        docker compose stop dbs_timescaledb 2>/dev/null || true
        echo "[INFO] TimescaleDB container stopped."
    fi
else
    echo "[NOTE] TimescaleDB container is left running for fast restart."
    echo "       Run './stop.sh --all' to also stop the Docker container."
fi

echo "=========================================================="
echo " DBS Stock Market Analytics services are stopped."
echo "=========================================================="
