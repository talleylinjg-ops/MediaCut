#!/usr/bin/env bash
# MediaCut 后端 VPS 部署脚本（在沙箱/本机执行，通过 SSH 操作目标 VPS）
#
# 用法：
#   bash edge/deploy-vps.sh root@<VPS_IP> [SSH端口]
#
# 前置：
#   - VPS 已开放 SSH；root 密码或已配置免密登录
#   - 环境变量 MEDIACUT_ENV_FILE 指向本地 .env 文件（含 DATABASE_URL 等），缺省使用 edge/vps.env
#
# 架构：
#   - 后端常驻 systemd（无休眠），监听 127.0.0.1:8000
#   - 数据库 Supabase Postgres（DATABASE_URL）
#   - 结果文件本地 + R2 双写；下载经 /api/v1/result 302 到 CF 边缘（不占 VPS 带宽）
#   - Cloudflare Worker 的 /api/* 回源本机 8000（ORIGIN=http://<VPS_IP>:8000）

set -euo pipefail

HOST="${1:?用法: bash edge/deploy-vps.sh root@<VPS_IP> [SSH端口]}"
PORT="${2:-22}"
ENV_FILE="${MEDIACUT_ENV_FILE:-edge/vps.env}"
REMOTE_DIR="/opt/mediacut"

[ -f "$ENV_FILE" ] || { echo "缺少环境变量文件: $ENV_FILE" >&2; exit 1; }

SSH="ssh -p $PORT -o StrictHostKeyChecking=accept-new"

echo "==> 1/4 安装系统依赖"
$SSH "$HOST" bash -s <<'REMOTE'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip ffmpeg curl >/dev/null
REMOTE

echo "==> 2/4 同步代码"
rsync -az -e "ssh -p $PORT" --delete backend/ "$HOST:$REMOTE_DIR/backend/"

echo "==> 3/4 配置环境与依赖"
$SSH "$HOST" bash -s <<REMOTE
set -e
mkdir -p $REMOTE_DIR
cat > $REMOTE_DIR/.env <<'ENVEOF'
$(cat "$ENV_FILE")
ENVEOF
chmod 600 $REMOTE_DIR/.env
cd $REMOTE_DIR/backend
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-render.txt
cat > /etc/systemd/system/mediacut.service <<'UNIT'
[Unit]
Description=MediaCut API
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/mediacut/backend
EnvironmentFile=/opt/mediacut/.env
ExecStart=/opt/mediacut/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable mediacut >/dev/null
REMOTE

echo "==> 4/5 启动与健康检查"
$SSH "$HOST" bash -s <<'REMOTE'
systemctl restart mediacut
sleep 4
systemctl is-active mediacut
curl -sf http://127.0.0.1:8000/health && echo " <- health OK"
REMOTE

echo "==> 5/5 Seed SAAS 开发者账号（didi AI 对接用）"
$SSH "$HOST" bash -c "cd $REMOTE_DIR/backend && set -a && . $REMOTE_DIR/.env && set +a && .venv/bin/python scripts/seed_saas.py"

echo "==> 完成。下一步：把 Worker 的 ORIGIN 指向 http://<该VPS_IP>:8000 并重新部署 Worker"
echo "==> SAAS 验证：curl http://<VPS_IP>:8000/api/v1/dev/key/info -H 'Authorization: Bearer <SAAS_KEY>'"
