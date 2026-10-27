#!/usr/bin/env bash
# ==============================================================================
# DBS Stock Market Analytics & Portfolio Management System — Unified Startup
# ==============================================================================
# Starts:
#   1. TimescaleDB Docker container (port 5434, if not already running)
#   2. FastAPI backend on http://127.0.0.1:8000 (using ./venv)
#   3. React/Vite frontend on http://localhost:5173 (using ./frontend)
#
# Usage:
#   ./start.sh
#
# Press Ctrl+C to cleanly stop all started processes.
# ==============================================================================

set -e

# Resolve project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BACKEND_PORT=8000
FRONTEND_PORT=5173
LOG_DIR="$PROJECT_ROOT/.logs"
PID_DIR="$PROJECT_ROOT/.run"

mkdir -p "$LOG_DIR" "$PID_DIR"

echo "=========================================================="
echo " DBS Stock Market Analytics — Unified Startup"
echo "=========================================================="
echo "[INFO] Project root: $PROJECT_ROOT"

# ------------------------------------------------------------------------------
# 1. Port conflict checks
# ------------------------------------------------------------------------------
check_port_available() {
    local port=$1
    local service_name=$2
    local pid
    pid=$(lsof -ti :"$port" -sTCP:LISTEN 2>/dev/null | head -n 1)
    if [ -n "$pid" ]; then
        local proc_info
        proc_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "Unknown process")
        echo "[ERROR] Port $port is already occupied by $proc_info (PID: $pid)."
        echo "        Cannot start $service_name."
        echo "        Please terminate the existing process or run ./stop.sh before starting."
        return 1
    fi
    return 0
}

echo "[INFO] Checking port availability..."
check_port_available "$BACKEND_PORT" "FastAPI backend" || exit 1
check_port_available "$FRONTEND_PORT" "React/Vite frontend" || exit 1
echo "[INFO] Ports $BACKEND_PORT and $FRONTEND_PORT are available."

# ------------------------------------------------------------------------------
# 2. Database & Docker checks
# ------------------------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        if docker ps --format '{{.Names}}' | grep -q "^dbs_timescaledb$"; then
            echo "[INFO] TimescaleDB container 'dbs_timescaledb' is already running (port 5434)."
        else
            echo "[INFO] Starting TimescaleDB container via docker compose..."
            docker compose up -d dbs_timescaledb
            # Wait up to 10s for container readiness
            docker_attempts=0
            until docker ps --filter "name=dbs_timescaledb" --filter "status=running" --format '{{.Names}}' | grep -q "^dbs_timescaledb$" || [ $docker_attempts -ge 10 ]; do
                sleep 1
                docker_attempts=$((docker_attempts + 1))
            done
            echo "[INFO] TimescaleDB container started."
        fi
    else
        echo "[WARN] Docker daemon is not accessible. If TimescaleDB is needed, please start Docker Desktop."
    fi
else
    echo "[WARN] Docker not found in PATH. Skipping Docker Compose container check."
fi

# Quick check on PostgreSQL relational DB (port 5435)
if lsof -ti :5435 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[INFO] PostgreSQL relational database detected on port 5435."
else
    echo "[WARN] PostgreSQL relational database not detected on port 5435. Backend will attempt connection based on .env."
fi

# ------------------------------------------------------------------------------
# 3. Environment & dependency verification
# ------------------------------------------------------------------------------
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo "[ERROR] Python virtual environment not found at $PROJECT_ROOT/venv."
    echo "        Please ensure python venv is configured."
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "[INFO] frontend/node_modules not found. Installing frontend dependencies..."
    (cd "$PROJECT_ROOT/frontend" && npm install)
fi

# ------------------------------------------------------------------------------
# 4. Process cleanup trap
# ------------------------------------------------------------------------------
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    local exit_code=${1:-0}
    echo ""
    echo "=========================================================="
    echo " Stopping DBS Stock Market Analytics services..."
    echo "=========================================================="

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "[INFO] Stopping frontend server (PID: $FRONTEND_PID)..."
        pkill -P "$FRONTEND_PID" 2>/dev/null || true
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "[INFO] Stopping backend server (PID: $BACKEND_PID)..."
        pkill -P "$BACKEND_PID" 2>/dev/null || true
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi

    # Small grace period for graceful termination
    sleep 1

    # Force kill if still lingering
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill -9 "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill -9 "$BACKEND_PID" 2>/dev/null || true
    fi

    rm -f "$PID_DIR/backend.pid" "$PID_DIR/frontend.pid" 2>/dev/null || true
    echo "[INFO] All services stopped cleanly."
    exit "$exit_code"
}

trap 'cleanup 0' INT TERM HUP

# ------------------------------------------------------------------------------
# 5. Start Backend Server
# ------------------------------------------------------------------------------
echo "[INFO] Starting FastAPI backend on http://127.0.0.1:$BACKEND_PORT..."
"$VENV_PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"

# ------------------------------------------------------------------------------
# 6. Wait for Backend Health Endpoint
# ------------------------------------------------------------------------------
echo "[INFO] Waiting for backend to become healthy (http://127.0.0.1:$BACKEND_PORT/api/health)..."
HEALTH_URL="http://127.0.0.1:$BACKEND_PORT/api/health"
MAX_HEALTH_ATTEMPTS=30
HEALTH_ATTEMPT=0
BACKEND_HEALTHY=false

while [ $HEALTH_ATTEMPT -lt $MAX_HEALTH_ATTEMPTS ]; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "[ERROR] Backend process terminated unexpectedly during startup."
        echo "----------------- Backend Log Snippet -----------------"
        tail -n 25 "$LOG_DIR/backend.log"
        echo "--------------------------------------------------------"
        cleanup 1
    fi

    RESPONSE=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>/dev/null || true)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        BACKEND_HEALTHY=true
        break
    fi

    HEALTH_ATTEMPT=$((HEALTH_ATTEMPT + 1))
    sleep 1
done

if [ "$BACKEND_HEALTHY" = false ]; then
    echo "[ERROR] Backend health check timed out after ${MAX_HEALTH_ATTEMPTS} seconds."
    echo "----------------- Backend Log Snippet -----------------"
    tail -n 25 "$LOG_DIR/backend.log"
    echo "--------------------------------------------------------"
    cleanup 1
fi

echo "[INFO] Backend is healthy and responding."

# ------------------------------------------------------------------------------
# 7. Start Frontend Dev Server
# ------------------------------------------------------------------------------
echo "[INFO] Starting React/Vite frontend on http://localhost:$FRONTEND_PORT..."
(cd "$PROJECT_ROOT/frontend" && npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1) > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"

# Wait for frontend readiness
MAX_FRONTEND_ATTEMPTS=20
F_ATTEMPT=0
FRONTEND_READY=false

while [ $F_ATTEMPT -lt $MAX_FRONTEND_ATTEMPTS ]; do
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "[ERROR] Frontend process terminated unexpectedly during startup."
        echo "----------------- Frontend Log Snippet -----------------"
        tail -n 25 "$LOG_DIR/frontend.log"
        echo "--------------------------------------------------------"
        cleanup 1
    fi

    F_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$FRONTEND_PORT/" 2>/dev/null || true)
    if [ "$F_CODE" = "200" ]; then
        FRONTEND_READY=true
        break
    fi

    F_ATTEMPT=$((F_ATTEMPT + 1))
    sleep 1
done

if [ "$FRONTEND_READY" = false ]; then
    echo "[ERROR] Frontend server failed to respond within ${MAX_FRONTEND_ATTEMPTS} seconds."
    echo "----------------- Frontend Log Snippet -----------------"
    tail -n 25 "$LOG_DIR/frontend.log"
    echo "--------------------------------------------------------"
    cleanup 1
fi

echo "[INFO] Frontend is ready and responding."

# ------------------------------------------------------------------------------
# 8. Ready Banner & Monitoring Loop
# ------------------------------------------------------------------------------
echo ""
echo "=========================================================="
echo " 🚀 DBS Stock Market Analytics is RUNNING!"
echo "=========================================================="
echo "  • Frontend Web UI:    http://localhost:$FRONTEND_PORT"
echo "  • Backend API:        http://127.0.0.1:$BACKEND_PORT"
echo "  • Interactive Docs:   http://127.0.0.1:$BACKEND_PORT/docs"
echo "  • Health Endpoint:    http://127.0.0.1:$BACKEND_PORT/api/health"
echo "  • Logs:               $LOG_DIR/"
echo "=========================================================="
echo " Press Ctrl+C to stop all services."
echo ""

# Keep running and monitor process liveness
while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "[ERROR] Backend server stopped unexpectedly (PID: $BACKEND_PID)."
        cleanup 1
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo "[ERROR] Frontend server stopped unexpectedly (PID: $FRONTEND_PID)."
        cleanup 1
    fi
    sleep 1
done
