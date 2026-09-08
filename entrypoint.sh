#!/bin/sh
set -e

PORT="${PORT:-8501}"
echo "=== Starting Mandea AI Streamlit App on 0.0.0.0:$PORT ==="

exec streamlit run app.py \
  --server.port="$PORT" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
