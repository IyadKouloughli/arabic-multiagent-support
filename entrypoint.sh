#!/usr/bin/env sh
set -e

# Default port to 8000 if not set (Cloud Run automatically injects $PORT=8080)
TARGET_PORT="${PORT:-8000}"

if [ "$APP_MODE" = "dashboard" ]; then
    echo "🚀 Launching Nawras Market Streamlit Dashboard on port ${TARGET_PORT}..."
    exec streamlit run src/ui/app.py --server.port "${TARGET_PORT}" --server.address 0.0.0.0 --server.headless true
else
    echo "🚀 Launching Nawras Market FastAPI API on port ${TARGET_PORT}..."
    exec uvicorn src.api.app:app --host 0.0.0.0 --port "${TARGET_PORT}"
fi
