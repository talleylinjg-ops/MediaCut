#!/usr/bin/env bash
# 校验「静态页面与原站完全一致」。
#
# 用法：
#   bash edge/verify-consistency.sh --origin http://localhost:8000
#       对比源站响应与本地 dist（验证源站输出 = 构建产物）。
#
#   bash edge/verify-consistency.sh --origin https://didimedia.com --edge https://edge.example.com
#       对比边缘响应与源站响应（部署后回归，验证边缘 = 原站）。
#
# 校验内容：dist 全部静态文件 + SPA 路由快照，逐项对比 HTTP 状态码、
# content-type 与响应体字节（md5）。发现差异时列出明细并以非零码退出。

set -uo pipefail

ORIGIN=""
EDGE=""
DIST="frontend/dist"
CURL_TIMEOUT=30

while [ $# -gt 0 ]; do
  case "$1" in
    --origin) ORIGIN="$2"; shift 2 ;;
    --edge) EDGE="$2"; shift 2 ;;
    --dist) DIST="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$ORIGIN" ] || [ ! -d "$DIST" ]; then
  echo "用法: bash edge/verify-consistency.sh --origin <源站URL> [--edge <边缘URL>] [--dist <dist目录>]" >&2
  exit 2
fi

ORIGIN="${ORIGIN%/}"
EDGE="${EDGE%/}"
SPA_ROUTES="/ /pricing /docs /register /playground /swagger"
PASS=0
FAIL=0
declare -a DIFFS=()

fetch_meta() {
  # $1=base $2=path -> 输出 "status|content-type|md5"
  local resp hdr body
  resp=$(mktemp)
  hdr=$(mktemp)
  curl -sS --max-time "$CURL_TIMEOUT" -o "$resp" -D "$hdr" -w '%{http_code}' "$1$2" > /dev/null 2>&1
  local status
  status=$(curl -sS --max-time "$CURL_TIMEOUT" -o /dev/null -w '%{http_code}' "$1$2" 2>/dev/null)
  local ctype
  ctype=$(grep -i '^content-type:' "$hdr" | head -1 | sed 's/^[Cc]ontent-[Tt]ype: *//' | tr -d '\r')
  local md5
  md5=$(md5sum "$resp" | cut -d' ' -f1)
  rm -f "$resp" "$hdr"
  echo "${status:-000}|${ctype:-}|${md5:-}"
}

report() {
  # $1=标签 $2=路径 $3=期望 $4=实际
  PASS=$((PASS + 1))
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

echo "== 校验目标 =="
echo "源站: $ORIGIN"
if [ -n "$EDGE" ]; then echo "边缘: $EDGE（对比边缘 vs 源站）"; else echo "对比: 源站 vs 本地 dist（$DIST）"; fi
echo

echo "== 1/3 dist 静态文件 =="
while IFS= read -r -d '' f; do
  rel="${f#"$DIST"/}"
  url="/$rel"
  local_md5=$(md5sum "$f" | cut -d' ' -f1)
  origin_meta=$(fetch_meta "$ORIGIN" "$url")
  o_status=$(echo "$origin_meta" | cut -d'|' -f1)
  o_body=$(echo "$origin_meta" | cut -d'|' -f3)
  if [ "$o_status" != "200" ]; then
    fail_item "源站状态" "$url" "200" "$o_status"
    continue
  fi
  if [ "$o_body" != "$local_md5" ]; then
    fail_item "源站字节" "$url" "$local_md5" "$o_body"
  else
    PASS=$((PASS + 1))
  fi
  if [ -n "$EDGE" ]; then
    edge_meta=$(fetch_meta "$EDGE" "$url")
    compare_pair "边缘对比" "$url" "$origin_meta" "$edge_meta"
  fi
done < <(find "$DIST" -type f -print0)

echo "== 2/3 SPA 路由快照 =="
index_meta=$(fetch_meta "$ORIGIN" "/")
for route in $SPA_ROUTES; do
  [ "$route" = "/" ] && continue
  origin_meta=$(fetch_meta "$ORIGIN" "$route")
  compare_pair "源站SPA" "$route" "$index_meta" "$origin_meta"
  if [ -n "$EDGE" ]; then
    edge_meta=$(fetch_meta "$EDGE" "$route")
    compare_pair "边缘SPA" "$route" "$index_meta" "$edge_meta"
  fi
done

echo "== 3/3 汇总 =="
echo "通过: $PASS  差异: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "---- 差异明细（格式: meta = status|content-type|md5）----"
  for d in "${DIFFS[@]}"; do echo "$d"; done
  exit 1
fi
echo "完全一致校验通过"
