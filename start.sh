#!/bin/bash
# 启动后端（端口 8000）与前端（端口 5173）
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$BACKEND_DIR/storage/results" ]; then
  mkdir -p "$BACKEND_DIR/storage/uploads" "$BACKEND_DIR/storage/results"
fi

echo "[1/2] 启动后端 API 服务 (http://localhost:8000)"
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "[2/2] 启动前端管理后台 (http://localhost:5173)"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

wait
