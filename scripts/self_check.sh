#!/usr/bin/env bash
# 「骂醒了么」本地/生产环境一键自测脚本
# 用法：
#   bash scripts/self_check.sh                              # 默认本地 http://localhost:8080
#   bash scripts/self_check.sh https://你的云托管域名        # 测生产
#
# 依赖：curl、python3（用于解析 JSON）

set -u

BASE_URL="${1:-http://localhost:8080}"
OPENID="self-check-$(date +%s)"
PASS=0
FAIL=0
TOTAL=0

# ---------- 颜色 ----------
if [ -t 1 ]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[0;33m'
  CYAN='\033[0;36m'
  NC='\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; CYAN=''; NC=''
fi

# ---------- 工具函数 ----------
_json_get() {
  # $1: JSON 字符串   $2: python 解析表达式 (obj -> value)
  python3 -c "
import json,sys
try:
    obj=json.loads(sys.stdin.read())
    print($2)
except Exception as e:
    print('__PARSE_ERROR__:'+str(e))
" <<< "$1"
}

check() {
  # $1: 用例名   $2: 期望描述   $3: 实际值   $4: 判定条件(pass|fail)
  TOTAL=$((TOTAL+1))
  if [ "$4" = "pass" ]; then
    PASS=$((PASS+1))
    printf "${GREEN}✅ [%02d] %-40s${NC} %s\n" "$TOTAL" "$1" "$3"
  else
    FAIL=$((FAIL+1))
    printf "${RED}❌ [%02d] %-40s${NC} 期望: %s | 实际: %s\n" "$TOTAL" "$1" "$2" "$3"
  fi
}

section() {
  printf "\n${CYAN}==== %s ====${NC}\n" "$1"
}

# ---------- 开场 ----------
printf "${YELLOW}"
cat <<'EOF'
╔════════════════════════════════════════════════╗
║   骂醒了么 · 环境自测脚本                       ║
╚════════════════════════════════════════════════╝
EOF
printf "${NC}"
echo "🎯 目标地址：$BASE_URL"
echo "🔑 测试 openid：$OPENID"

# ---------- 1. 健康检查 ----------
section "1. 基础健康"
resp=$(curl -sS -m 10 "$BASE_URL/actuator/health" || echo "")
status=$(_json_get "$resp" "obj.get('status','')")
if [ "$status" = "UP" ]; then
  check "健康检查 /actuator/health" "UP" "$status" "pass"
else
  check "健康检查 /actuator/health" "UP" "$resp" "fail"
  echo "❗ 服务不可达，后续用例跳过。请先启动后端。"
  exit 1
fi

# ---------- 2. 风格列表 ----------
resp=$(curl -sS -m 10 "$BASE_URL/api/roast/styles")
code=$(_json_get "$resp" "obj.get('code',-1)")
count=$(_json_get "$resp" "len(obj.get('data',[]))")
if [ "$code" = "0" ] && [ "$count" -ge "6" ]; then
  check "风格列表 /api/roast/styles" "code=0,风格>=6" "code=$code,count=$count" "pass"
else
  check "风格列表 /api/roast/styles" "code=0,风格>=6" "code=$code,count=$count" "fail"
fi

# ---------- 3. 卡片模板列表 ----------
resp=$(curl -sS -m 10 "$BASE_URL/api/card/templates")
code=$(_json_get "$resp" "obj.get('code',-1)")
count=$(_json_get "$resp" "len(obj.get('data',[]))")
if [ "$code" = "0" ] && [ "$count" -ge "1" ]; then
  check "卡片模板 /api/card/templates" "code=0,templates>=1" "code=$code,count=$count" "pass"
else
  check "卡片模板 /api/card/templates" "code=0,templates>=1" "code=$code,count=$count" "fail"
fi

# ---------- 4. 骂醒接口（自定义风格，避免烧 AI 额度） ----------
section "2. 核心业务"
payload='{"userInput":"自测占位内容-'$OPENID'","style":"custom"}'
resp=$(curl -sS -m 15 -X POST "$BASE_URL/api/roast" \
  -H "Content-Type: application/json" \
  -H "X-WX-OPENID: $OPENID" \
  -d "$payload")
code=$(_json_get "$resp" "obj.get('code',-1)")
roast_id=$(_json_get "$resp" "obj.get('data',{}).get('roastId','')")
if [ "$code" = "0" ] && [ -n "$roast_id" ] && [ "$roast_id" != "__PARSE_ERROR__" ]; then
  check "骂醒 /api/roast (custom)" "code=0,有roastId" "roastId=$roast_id" "pass"
else
  check "骂醒 /api/roast (custom)" "code=0,有roastId" "code=$code" "fail"
  echo "❗ 骂醒失败，跳过后续依赖用例。响应: $resp"
  roast_id=""
fi

# ---------- 5. 配额查询 ----------
resp=$(curl -sS -m 10 "$BASE_URL/api/roast/quota" -H "X-WX-OPENID: $OPENID")
code=$(_json_get "$resp" "obj.get('code',-1)")
used=$(_json_get "$resp" "obj.get('data',{}).get('used',-1)")
if [ "$code" = "0" ] && [ "$used" -ge "1" ]; then
  check "配额 /api/roast/quota" "code=0,used>=1" "used=$used" "pass"
else
  check "配额 /api/roast/quota" "code=0,used>=1" "code=$code,used=$used" "fail"
fi

# ---------- 6. 卡片生成 ----------
if [ -n "$roast_id" ]; then
  payload="{\"roastId\":\"$roast_id\",\"templateKey\":\"chat\"}"
  resp=$(curl -sS -m 30 -X POST "$BASE_URL/api/card" \
    -H "Content-Type: application/json" \
    -H "X-WX-OPENID: $OPENID" \
    -d "$payload")
  code=$(_json_get "$resp" "obj.get('code',-1)")
  image_url=$(_json_get "$resp" "obj.get('data',{}).get('imageUrl','')")
  if [ "$code" = "0" ] && [ -n "$image_url" ] && [ "$image_url" != "__PARSE_ERROR__" ]; then
    check "卡片生成 /api/card (chat)" "code=0,有imageUrl" "imageUrl=$image_url" "pass"
  else
    check "卡片生成 /api/card (chat)" "code=0,有imageUrl" "code=$code" "fail"
  fi
else
  check "卡片生成 /api/card (chat)" "依赖上一步" "skipped" "fail"
fi

# ---------- 7. 历史列表 ----------
section "3. 用户体系"
resp=$(curl -sS -m 10 "$BASE_URL/api/history?page=1&size=10" -H "X-WX-OPENID: $OPENID")
code=$(_json_get "$resp" "obj.get('code',-1)")
total=$(_json_get "$resp" "obj.get('data',{}).get('total',-1)")
if [ "$code" = "0" ] && [ "$total" -ge "1" ]; then
  check "历史 /api/history" "code=0,total>=1" "total=$total" "pass"
else
  check "历史 /api/history" "code=0,total>=1" "code=$code,total=$total" "fail"
fi

# ---------- 8. 收藏 ----------
if [ -n "$roast_id" ]; then
  resp=$(curl -sS -m 10 -X POST "$BASE_URL/api/favorite/$roast_id" -H "X-WX-OPENID: $OPENID")
  code=$(_json_get "$resp" "obj.get('code',-1)")
  if [ "$code" = "0" ]; then
    check "收藏 POST /api/favorite/{id}" "code=0" "ok" "pass"
  else
    check "收藏 POST /api/favorite/{id}" "code=0" "code=$code" "fail"
  fi

  resp=$(curl -sS -m 10 "$BASE_URL/api/favorites?page=1&size=10" -H "X-WX-OPENID: $OPENID")
  code=$(_json_get "$resp" "obj.get('code',-1)")
  total=$(_json_get "$resp" "obj.get('data',{}).get('total',-1)")
  if [ "$code" = "0" ] && [ "$total" -ge "1" ]; then
    check "收藏列表 /api/favorites" "code=0,total>=1" "total=$total" "pass"
  else
    check "收藏列表 /api/favorites" "code=0,total>=1" "code=$code,total=$total" "fail"
  fi

  resp=$(curl -sS -m 10 -X DELETE "$BASE_URL/api/favorite/$roast_id" -H "X-WX-OPENID: $OPENID")
  code=$(_json_get "$resp" "obj.get('code',-1)")
  if [ "$code" = "0" ]; then
    check "取消收藏 DELETE /api/favorite/{id}" "code=0" "ok" "pass"
  else
    check "取消收藏 DELETE /api/favorite/{id}" "code=0" "code=$code" "fail"
  fi
fi

# ---------- 9. 用户统计 ----------
resp=$(curl -sS -m 10 "$BASE_URL/api/user/stats" -H "X-WX-OPENID: $OPENID")
code=$(_json_get "$resp" "obj.get('code',-1)")
if [ "$code" = "0" ]; then
  history_cnt=$(_json_get "$resp" "obj.get('data',{}).get('historyCount',0)")
  check "用户统计 /api/user/stats" "code=0" "historyCount=$history_cnt" "pass"
else
  check "用户统计 /api/user/stats" "code=0" "code=$code" "fail"
fi

# ---------- 10. 用户隔离（防越权） ----------
if [ -n "$roast_id" ]; then
  OTHER_OPENID="other-user-$(date +%s)"
  resp=$(curl -sS -m 10 -X DELETE "$BASE_URL/api/history/$roast_id" -H "X-WX-OPENID: $OTHER_OPENID")
  code=$(_json_get "$resp" "obj.get('code',-1)")
  # 期望：非本人删除应失败（code != 0）或删除0条
  if [ "$code" != "0" ]; then
    check "越权删除防护" "非本人应失败" "code=$code (拒绝)" "pass"
  else
    # 也可能 code=0 但 data.deleted=0，看后端实现
    deleted=$(_json_get "$resp" "obj.get('data',{}).get('deleted',-1)")
    if [ "$deleted" = "0" ]; then
      check "越权删除防护" "非本人应失败" "deleted=0 (静默拒绝)" "pass"
    else
      check "越权删除防护" "非本人应失败" "code=$code,deleted=$deleted (⚠️ 越权!)" "fail"
    fi
  fi
fi

# ---------- 11. 敏感词过滤 ----------
section "4. 合规防线"
payload='{"userInput":"我想死了想不开","style":"yiju"}'
resp=$(curl -sS -m 15 -X POST "$BASE_URL/api/roast" \
  -H "Content-Type: application/json" \
  -H "X-WX-OPENID: crisis-check-$(date +%s)" \
  -d "$payload")
# 心理危机词兜底：后端会返回 code=1002 + message 中含热线，data 为 null
code=$(_json_get "$resp" "obj.get('code',-1)")
message=$(_json_get "$resp" "obj.get('message','')")
if [ "$code" != "0" ] && echo "$message" | grep -q "400-161-9995\|援助热线\|心理"; then
  check "心理危机词兜底" "code!=0且message含热线" "code=$code (已触发)" "pass"
else
  check "心理危机词兜底" "code!=0且message含热线" "code=$code (未触发⚠️危险)" "fail"
fi

# ---------- 汇总 ----------
echo ""
printf "${CYAN}════════ 自测汇总 ════════${NC}\n"
printf "  总计：%d   ${GREEN}通过：%d${NC}   ${RED}失败：%d${NC}\n" "$TOTAL" "$PASS" "$FAIL"
echo ""

if [ "$FAIL" -eq "0" ]; then
  printf "${GREEN}🎉 全部通过！可以进入下一步（真机手工验证 + 提审）${NC}\n"
  exit 0
else
  printf "${RED}⚠️  有 %d 项失败，请修复后重试${NC}\n" "$FAIL"
  exit 2
fi
