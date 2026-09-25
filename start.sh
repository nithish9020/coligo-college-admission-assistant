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

# 1. Start FastAPI backend
uvicorn api.main:app --host 127.0.0.1 --port 8001 --no-access-log &
FASTAPI_PID=$!

# 2. Start Streamlit admin portal
streamlit run administration_portal/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# Graceful termination handling
cleanup() {
    echo "Stopping Coligo Unified Service..."
    kill -TERM "$FASTAPI_PID" "$STREAMLIT_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 3. Start Nginx in foreground to keep container alive
exec nginx -g "daemon off;"
