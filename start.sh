#!/bin/bash
set -e

PORT=${PORT:-8000}
export PORT

# Render / substitute PORT into nginx configuration
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "Starting Coligo Unified Service on public port ${PORT}..."
echo " - FastAPI starting on internal 127.0.0.1:8001"
echo " - Streamlit Portal starting on internal 127.0.0.1:8501"

export COLIGO_API_BASE_URL="http://127.0.0.1:8001"
export PYTHONPATH="/app:${PYTHONPATH:-}"

# 1. Start FastAPI backend
uvicorn api.main:app --host 127.0.0.1 --port 8001 --no-access-log &
FASTAPI_PID=$!

# 2. Start Streamlit admin portal
streamlit run administration_portal/portal.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# 3. Wait for FastAPI to be ready (up to 60s)
echo "Waiting for FastAPI to be ready..."
for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8001/health > /dev/null 2>&1; then
        echo "FastAPI is ready (${i}s)"
        break
    fi
    sleep 1
done

# 4. Wait for Streamlit to be ready (up to 60s)
echo "Waiting for Streamlit to be ready..."
for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8501/_stcore/health > /dev/null 2>&1; then
        echo "Streamlit is ready (${i}s)"
        break
    fi
    sleep 1
done

# Graceful termination handling
cleanup() {
    echo "Stopping Coligo Unified Service..."
    kill -TERM "$FASTAPI_PID" "$STREAMLIT_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 5. Start Nginx in foreground to keep container alive
exec nginx -g "daemon off;"
