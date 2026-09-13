#!/usr/bin/env bash
set -euo pipefail

# MediaCut API 生产部署脚本（Ubuntu 22.04+ / Debian 12+）
# 用法：
#   sudo bash deploy/install.sh --domain didimedia.com
# 可选参数：
#   --domain <域名>          必填，用于 Caddy 自动申请 HTTPS 证书
#   --dir <安装目录>         默认 /opt/mediacut
#   --user <运行用户>        默认 mediacut
#   --admin-password <密码>  管理员密码，默认随机生成并打印
#   --skip-frontend          跳过前端构建
#   --preheat-models         启动后预热 AI 模型（下载较慢，建议首次执行）

DOMAIN=""
INSTALL_DIR="/opt/mediacut"
RUN_USER="mediacut"
ADMIN_PASSWORD=""
SKIP_FRONTEND=0
PREHEAT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --user)
      RUN_USER="$2"
      shift 2
      ;;
    --admin-password)
      ADMIN_PASSWORD="$2"
      shift 2
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    --preheat-models)
      PREHEAT=1
      shift
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

if [ -z "$DOMAIN" ]; then
  echo "错误：必须通过 --domain 指定域名"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "错误：请使用 root 或 sudo 运行"
  exit 1
fi

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -d "$SRC_DIR/backend" ] || [ ! -d "$SRC_DIR/frontend" ]; then
  echo "错误：请在项目根目录下运行本脚本"
  exit 1
fi

echo "[1/9] 安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip ffmpeg git curl rsync ca-certificates gnupg openssl debian-keyring debian-archive-keyring apt-transport-https

echo "[2/9] 安装 Node.js"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

echo "[3/9] 安装 Caddy"
if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-get install -y caddy
fi

echo "[4/9] 创建运行用户与安装目录"
if ! id -u "$RUN_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$RUN_USER"
fi
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'frontend/dist' \
  --exclude 'backend/storage' \
  --exclude 'backend/*.db*' \
  "$SRC_DIR/" "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/backend/storage/uploads" "$INSTALL_DIR/backend/storage/results"

echo "[5/9] 创建 Python 虚拟环境并安装依赖"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel
"$INSTALL_DIR/venv/bin/pip" install --index-url https://download.pytorch.org/whl/cpu torch torchvision
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"

echo "[6/9] 构建前端"
if [ "$SKIP_FRONTEND" -eq 0 ]; then
  cd "$INSTALL_DIR/frontend"
  npm install
  npm run build
fi

echo "[7/9] 写入环境变量"
ENV_DIR="/etc/mediacut"
ENV_FILE="$ENV_DIR/mediacut.env"
mkdir -p "$ENV_DIR"
if [ -z "$ADMIN_PASSWORD" ]; then
  ADMIN_PASSWORD="$(openssl rand -hex 8)"
fi
JWT_SECRET="$(openssl rand -hex 32)"
cat > "$ENV_FILE" <<EOF
MODELSCOPE_API_TOKEN=
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD
JWT_SECRET=$JWT_SECRET
ALLOWED_ORIGINS=https://$DOMAIN
WHISPER_MODEL=small
EOF
chmod 600 "$ENV_FILE"
chown root:root "$ENV_FILE"

echo "[8/9] 安装 systemd 服务"
sed "s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__RUN_USER__|$RUN_USER|g" "$INSTALL_DIR/deploy/mediacut.service" > /etc/systemd/system/mediacut.service
systemctl daemon-reload
systemctl enable mediacut

echo "[9/9] 配置 Caddy 反向代理"
sed "s|__DOMAIN__|$DOMAIN|g" "$INSTALL_DIR/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl enable caddy
systemctl restart caddy

chown -R "$RUN_USER:$RUN_USER" "$INSTALL_DIR"
systemctl restart mediacut

if [ "$PREHEAT" -eq 1 ]; then
  echo "[附加] 预热 AI 模型（首次下载较慢）"
  sudo -u "$RUN_USER" "$INSTALL_DIR/venv/bin/python" - <<'PY'
from faster_whisper import WhisperModel
import os
WhisperModel(os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
from rembg import new_session
new_session("u2net")
print("模型预热完成")
PY
fi

echo
echo "部署完成"
echo "  站点：https://$DOMAIN"
echo "  管理后台：https://$DOMAIN/login"
echo "  管理员账号：admin"
echo "  管理员密码：$ADMIN_PASSWORD"
echo "  环境变量文件：$ENV_FILE"
echo "  服务状态：systemctl status mediacut"
echo "  实时日志：journalctl -u mediacut -f"
echo "  提示：可在管理后台账号中心配置 ModelScope Token，或修改 $ENV_FILE 后执行 systemctl restart mediacut"
