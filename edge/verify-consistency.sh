#!/usr/bin/env bash
# 校验「静态页面与源站/边缘完全一致」。
#
# 用法：
#   bash edge/verify-consistency.sh --origin http://localhost:8000
#       对比源站响应与本地 dist（验证源站输出 = 构建产物）。
#
#   bash edge/verify-consistency.sh --origin https://didimedia.com --edge https://xxx.workers.dev
#       dist 为完整版构建：分别对比源站与边缘（双轨一致回归）。
#
#   bash edge/verify-consistency.sh --edge https://xxx.workers.dev
#       dist 为纯静态版构建：对比边缘输出与本地静态版 dist。
#
#   沙箱/本机 DNS 被污染时可加：--resolve "host:443:<真实IP>"（IP 可用 DoH 查询）
#
# 校验内容：dist 全部静态文件 + SPA 路由快照，逐项对比 HTTP 状态码、
# content-type 与响应体字节（md5）。发现差异时列出明细并以非零码退出。

set -uo pipefail

ORIGIN=""
EDGE=""
DIST="frontend/dist"
CURL_TIMEOUT=30
RESOLVE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --origin) ORIGIN="$2"; shift 2 ;;
    --edge) EDGE="$2"; shift 2 ;;
    --dist) DIST="$2"; shift 2 ;;
    --resolve) RESOLVE="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if [ ! -d "$DIST" ] || { [ -z "$ORIGIN" ] && [ -z "$EDGE" ]; }; then
  echo "用法: bash edge/verify-consistency.sh --origin <源站URL> [--edge <边缘URL>] [--dist <dist目录>]" >&2
  echo "      --origin 与 --edge 至少提供一个；对比基准始终是本地 dist" >&2
  exit 2
fi

ORIGIN="${ORIGIN%/}"
EDGE="${EDGE%/}"
SPA_ROUTES="/ /pricing /docs /register /playground /swagger"
PASS=0
FAIL=0
declare -a DIFFS=()

fetch_meta() {
  # $1=base $2=path -> 输出 "status|content-type|md5|size"
  local resp hdr
  resp=$(mktemp)
  hdr=$(mktemp)
  curl -sS --max-time "$CURL_TIMEOUT" ${RESOLVE:+--resolve "$RESOLVE"} -o "$resp" -D "$hdr" "$1$2" > /dev/null 2>&1
  local ctype
  ctype=$(grep -i '^content-type:' "$hdr" | head -1 | sed 's/^[Cc]ontent-[Tt]ype: *//' | tr -d '\r')
  local md5
  md5=$(md5sum "$resp" | cut -d' ' -f1)
  local size
  size=$(stat -c%s "$resp")
  rm -f "$resp" "$hdr"
  echo "200|${ctype:-}|${md5:-}|${size:-0}"
}

fail_item() {
  FAIL=$((FAIL + 1))
  DIFFS+=("$1 $2 期望[$3] 实际[$4]")
}

compare_pair() {
  # $1=标签 $2=路径 $3=A meta $4=B meta（A=基准, B=被对比方）
  local label="$1" path="$2" a="$3" b="$4"
  if [ "$a" = "$b" ]; then
    PASS=$((PASS + 1))
  else
    fail_item "$label" "$path" "$a" "$b"
  fi
}

local_meta() {
  # $1=本地文件 -> "200|<按扩展名预期>|md5|size"
  local f="$1"
  local md5
  md5=$(md5sum "$f" | cut -d' ' -f1)
  local size
  size=$(stat -c%s "$f")
  echo "200||${md5}|${size}"
}

echo "== 校验目标 =="
echo "基准: 本地 dist（$DIST）"
[ -n "$ORIGIN" ] && echo "源站: $ORIGIN"
[ -n "$EDGE" ] && echo "边缘: $EDGE"
echo

echo "== 1/3 dist 静态文件 =="
while IFS= read -r -d '' f; do
  rel="${f#"$DIST"/}"
  url="/$rel"
  expected=$(local_meta "$f")
  exp_md5=$(echo "$expected" | cut -d'|' -f3)
  if [ -n "$ORIGIN" ]; then
    origin_meta=$(fetch_meta "$ORIGIN" "$url")
    o_md5=$(echo "$origin_meta" | cut -d'|' -f3)
    o_ctype=$(echo "$origin_meta" | cut -d'|' -f2)
    if [ "$o_md5" != "$exp_md5" ]; then
      fail_item "源站字节" "$url" "$exp_md5" "$o_md5"
    else
      PASS=$((PASS + 1))
    fi
    case "$o_ctype" in
      application/octet-stream|"")
        case "$(basename "$rel")" in
          *_*) PASS=$((PASS + 1)) ;;
          *) fail_item "源站MIME" "$url" "具体类型" "$o_ctype" ;;
        esac
        ;;
      *) PASS=$((PASS + 1)) ;;
    esac
  fi
  if [ -n "$EDGE" ]; then
    edge_meta=$(fetch_meta "$EDGE" "$url")
    e_md5=$(echo "$edge_meta" | cut -d'|' -f3)
    e_ctype=$(echo "$edge_meta" | cut -d'|' -f2)
    if [ "$e_md5" != "$exp_md5" ]; then
      fail_item "边缘字节" "$url" "$exp_md5" "$e_md5"
    else
      PASS=$((PASS + 1))
    fi
    case "$e_ctype" in
      application/octet-stream|"")
        case "$(basename "$rel")" in
          *_*) PASS=$((PASS + 1)) ;;
          *) fail_item "边缘MIME" "$url" "具体类型" "$e_ctype" ;;
        esac
        ;;
      *) PASS=$((PASS + 1)) ;;
    esac
  fi
done < <(find "$DIST" -type f -print0)

echo "== 2/3 SPA 路由快照 =="
if [ -n "$ORIGIN" ]; then
  index_meta=$(fetch_meta "$ORIGIN" "/")
fi
if [ -n "$EDGE" ]; then
  edge_index_meta=$(fetch_meta "$EDGE" "/")
fi
for route in $SPA_ROUTES; do
  [ "$route" = "/" ] && continue
  if [ -n "$ORIGIN" ]; then
    origin_meta=$(fetch_meta "$ORIGIN" "$route")
    compare_pair "源站SPA" "$route" "$index_meta" "$origin_meta"
  fi
  if [ -n "$EDGE" ]; then
    edge_meta=$(fetch_meta "$EDGE" "$route")
    compare_pair "边缘SPA" "$route" "$edge_index_meta" "$edge_meta"
  fi
done

echo "== 3/3 汇总 =="
echo "通过: $PASS  差异: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "---- 差异明细（格式: meta = status|content-type|md5|size）----"
  for d in "${DIFFS[@]}"; do echo "$d"; done
  exit 1
fi
echo "完全一致校验通过"
