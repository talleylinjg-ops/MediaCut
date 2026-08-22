#!/bin/bash
# 单端口启动：后端 API（8000）同时托管前端静态站点与 Swagger 文档
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$BACKEND_DIR/storage/results" ]; then
  mkdir -p "$BACKEND_DIR/storage/uploads" "$BACKEND_DIR/storage/results"
fi

echo "[1/2] 构建前端静态产物"
cd "$FRONTEND_DIR"
npm run build

echo "[2/2] 启动后端 API 服务 (http://localhost:8000)"
cd "$BACKEND_DIR"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
