#!/bin/bash
# ── [BILLING GUARD 4/4] Claude Pro OAuth 검증 ──────────────────────────────
# setup-vps.sh에서 orchestrator 실행 직전에 호출됨
# 실패 시 exit 1 → claude 실행 차단

CREDENTIALS="/home/dgm/.claude/.credentials.json"
DGM_ENV="/home/dgm/.config/dgm.env"

echo "▶ [billing-guard] Claude Pro 과금 모드 검증 중..."

# 1. 환경변수에 API 키가 있으면 차단
if [ -n "$ANTHROPIC_API_KEY" ]; then
  echo "❌ [billing-guard] ANTHROPIC_API_KEY 환경변수 감지!"
  echo "   API 키가 있으면 Claude Pro 대신 API 과금됩니다."
  echo "   해결: unset ANTHROPIC_API_KEY"
  exit 1
fi

# 2. dgm.env에 API 키가 남아있으면 제거 후 경고
if grep -q "ANTHROPIC_API_KEY" "$DGM_ENV" 2>/dev/null; then
  echo "⚠  [billing-guard] dgm.env에 API 키 감지 → 제거 중..."
  sed -i '/ANTHROPIC_API_KEY/d' "$DGM_ENV"
  echo "   ✓ 제거 완료"
fi

# 3. OAuth credentials 존재 여부
if [ ! -f "$CREDENTIALS" ]; then
  echo "❌ [billing-guard] OAuth credentials 파일 없음!"
  echo "   해결: claude 실행 후 /login → 옵션 1(Claude Pro)"
  exit 1
fi

# 4. credentials에서 subscriptionType 확인
SUBSCRIPTION=$(python3 -c "
import json, sys
try:
    d = json.load(open('$CREDENTIALS'))
    # claudeAiOauth.subscriptionType 구조
    oauth = d.get('claudeAiOauth', d)
    print(oauth.get('subscriptionType', 'unknown'))
except Exception as e:
    print('error')
" 2>/dev/null)

if [ "$SUBSCRIPTION" = "pro" ]; then
  echo "✅ [billing-guard] Claude Pro OAuth 확인됨 — API 과금 없음"
elif [ "$SUBSCRIPTION" = "unknown" ] || [ "$SUBSCRIPTION" = "error" ]; then
  echo "⚠  [billing-guard] subscriptionType 확인 불가 ($SUBSCRIPTION) — 계속 진행"
else
  echo "⚠  [billing-guard] subscriptionType: $SUBSCRIPTION (pro 아님)"
  echo "   Claude Pro 계정으로 로그인되지 않았을 수 있습니다."
fi

exit 0
