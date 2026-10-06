#!/usr/bin/env bash
# MediaCut 边缘镜像一键部署：dist → R2，然后部署 Worker
#
# 用法：
#   export CLOUDFLARE_API_TOKEN=...     # 需 Workers Scripts:Edit + R2:Edit
#   export CLOUDFLARE_ACCOUNT_ID=...
#   bash edge/deploy-edge.sh            # 用现有 frontend/dist
#   bash edge/deploy-edge.sh --build    # 先重新构建前端再上传
#   bash edge/deploy-edge.sh --build --static   # 构建纯静态展示版（隐藏注册/试用/控制台等后端入口）并上传
#
# 只上传、不部署 Worker：bash edge/deploy-edge.sh --skip-deploy
# 只部署、不上传：       bash edge/deploy-edge.sh --skip-upload

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKER_DIR="$ROOT_DIR/edge/worker"
DIST_DIR="$ROOT_DIR/frontend/dist"

BUILD=0
SKIP_UPLOAD=0
SKIP_DEPLOY=0
STATIC_BUILD=0
for arg in "$@"; do
  case "$arg" in
    --build) BUILD=1 ;;
    --static) STATIC_BUILD=1 ;;
    --skip-upload) SKIP_UPLOAD=1 ;;
    --skip-deploy) SKIP_DEPLOY=1 ;;
    *) echo "未知参数: $arg" >&2; exit 2 ;;
  esac
done

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "缺少 CLOUDFLARE_API_TOKEN（需 Workers Scripts:Edit 与 R2:Edit 权限）" >&2
  exit 1
fi
if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  echo "缺少 CLOUDFLARE_ACCOUNT_ID（可用 npx wrangler whoami 查看）" >&2
  exit 1
fi

if [[ "$BUILD" == "1" ]]; then
  if [[ "$STATIC_BUILD" == "1" ]]; then
    echo "==> 构建前端（纯静态展示版，无后端功能入口）"
    (cd "$ROOT_DIR/frontend" && npm run build:static)
  else
    echo "==> 构建前端"
    (cd "$ROOT_DIR/frontend" && npm run build)
  fi
fi

if [[ ! -f "$DIST_DIR/index.html" ]]; then
  echo "未找到 $DIST_DIR/index.html，请先构建前端或加 --build" >&2
  exit 1
fi

BUCKET="$(grep -E '^\s*bucket_name' "$WORKER_DIR/wrangler.toml" | head -1 | sed -E 's/.*=\s*"([^"]+)".*/\1/')"
if [[ -z "$BUCKET" ]]; then
  echo "无法从 wrangler.toml 解析 bucket_name" >&2
  exit 1
fi

content_type_for() {
  case "${1##*.}" in
    html) echo 'text/html; charset=utf-8' ;;
    js|mjs) echo 'text/javascript; charset=utf-8' ;;
    css) echo 'text/css; charset=utf-8' ;;
    json|map) echo 'application/json; charset=utf-8' ;;
    txt) echo 'text/plain; charset=utf-8' ;;
    xml) echo 'application/xml' ;;
    svg) echo 'image/svg+xml' ;;
    png) echo 'image/png' ;;
    jpg|jpeg) echo 'image/jpeg' ;;
    webp) echo 'image/webp' ;;
    gif) echo 'image/gif' ;;
    ico) echo 'image/vnd.microsoft.icon' ;;
    webmanifest) echo 'application/manifest+json' ;;
    woff2) echo 'font/woff2' ;;
    woff) echo 'font/woff' ;;
    *) echo 'application/octet-stream' ;;
  esac
}

if [[ "$SKIP_UPLOAD" != "1" ]]; then
  echo "==> 确保 R2 桶存在: $BUCKET"
  npx --yes wrangler r2 bucket create "$BUCKET" 2>/dev/null || true

  # 带重试的对象上传：网络抖动时最多重试 3 次，全部失败则终止
  r2_put() {
    local key="$1" file="$2" ct="$3" attempt=1
    while true; do
      if npx --yes wrangler r2 object put "$BUCKET/$key" \
        --file "$file" --content-type "$ct" --remote --force >/dev/null 2>&1; then
        return 0
      fi
      if [[ $attempt -ge 3 ]]; then
        echo "上传失败: $key（已重试 3 次）" >&2
        return 1
      fi
      echo "    上传失败，5 秒后重试 ($key, 第 $attempt 次)" >&2
      attempt=$((attempt + 1))
      sleep 5
    done
  }

  # 可压缩类型：上传原始对象的同时生成 .gz / .br 预压缩副本（Worker 按客户端能力协商）
  if command -v brotli >/dev/null 2>&1; then
    HAS_BROTLI=1
  else
    HAS_BROTLI=0
    echo "    （未安装 brotli，跳过 .br 副本，仅上传 .gz）"
  fi
  COMPRESS_RE='\.(html|js|mjs|css|json|map|txt|xml|svg|webmanifest)$'
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  echo "==> 上传 dist → R2 ($BUCKET)"
  count=0
  while IFS= read -r -d '' file; do
    rel="${file#"$DIST_DIR"/}"
    ct="$(content_type_for "$rel")"
    r2_put "$rel" "$file" "$ct"
    count=$((count + 1))
    echo "    $rel  ($ct)"

    if [[ "$rel" =~ $COMPRESS_RE ]]; then
      gzip -9 -c "$file" > "$TMP_DIR/gz.bin"
      r2_put "$rel.gz" "$TMP_DIR/gz.bin" "$ct"
      count=$((count + 1))
      echo "    $rel.gz  ($ct, gzip)"
      if [[ "$HAS_BROTLI" == "1" ]]; then
        brotli -q 11 -c "$file" > "$TMP_DIR/br.bin"
        r2_put "$rel.br" "$TMP_DIR/br.bin" "$ct"
        count=$((count + 1))
        echo "    $rel.br  ($ct, brotli)"
      fi
    fi
  done < <(find "$DIST_DIR" -type f -print0 | sort -z)
  echo "==> 已上传 $count 个对象（含压缩副本）"
fi

if [[ "$SKIP_DEPLOY" != "1" ]]; then
  echo "==> 部署 Worker"
  (cd "$WORKER_DIR" && npx --yes wrangler deploy)
fi

echo "==> 完成"
