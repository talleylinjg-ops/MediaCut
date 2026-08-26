#!/bin/bash
set -u
cd "$(dirname "$0")"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting uvicorn..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  code=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] uvicorn exited with code $code, restarting in 3s..."
  sleep 3
done
