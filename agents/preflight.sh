#!/bin/bash
# DGM VPS 사전점검 — 파이프라인 실행 전 상태를 읽기 전용으로 확인한다.
# setup-vps.sh처럼 세션을 만들거나 죽이지 않는다 — 순수 진단용.
# 사용법: bash /home/dgm/suno-api/agents/preflight.sh

PROJECT_DIR="/home/dgm/suno-api"
SESSION="dgm"
CREDENTIALS="/home/dgm/.claude/.credentials.json"
DGM_ENV="/home/dgm/.config/dgm.env"

WARN=0
FAIL=0

ok()   { echo "  ✅ $1"; }
warn() { echo "  ⚠  $1"; WARN=$((WARN+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "════════════════════════════════════════════════"
echo "  DGM VPS 사전점검 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════"

# ── 1. tmux dgm 세션 ────────────────────────────────────────────────────
echo ""
echo "▶ tmux 세션"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  WINDOW_COUNT=$(tmux list-windows -t "$SESSION" 2>/dev/null | wc -l)
  ok "세션 '$SESSION' 실행 중 (창 ${WINDOW_COUNT}개)"
  MISSING_WINDOWS=""
  for w in control-room suno-server orchestrator logs limit-watcher completion-watcher; do
    tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -qx "$w" || MISSING_WINDOWS="$MISSING_WINDOWS $w"
  done
  if [ -z "$MISSING_WINDOWS" ]; then
    ok "필수 창 6개 모두 존재"
  else
    warn "누락된 창:$MISSING_WINDOWS"
  fi
else
  bad "세션 '$SESSION' 없음 — setup-vps.sh 재실행 필요 (/vps-tmux-connect 스킬 참고)"
fi

# ── 2. Claude Pro OAuth / API 키 과금 위험 ──────────────────────────────
echo ""
echo "▶ 과금 모드 (Claude Pro OAuth)"
if [ -n "$ANTHROPIC_API_KEY" ]; then
  bad "현재 셸에 ANTHROPIC_API_KEY 설정됨 — unset 필요"
else
  ok "현재 셸에 ANTHROPIC_API_KEY 없음"
fi

if grep -q "ANTHROPIC_API_KEY" "$DGM_ENV" 2>/dev/null; then
  bad "dgm.env에 ANTHROPIC_API_KEY 잔존 (2026-07-04 26M 토큰 소진 사고 재현 위험)"
else
  ok "dgm.env에 API 키 없음"
fi

if [ -f "$CREDENTIALS" ]; then
  SUBSCRIPTION=$(python3 -c "
import json
try:
    d = json.load(open('$CREDENTIALS'))
    oauth = d.get('claudeAiOauth', d)
    print(oauth.get('subscriptionType', 'unknown'))
except Exception:
    print('error')
" 2>/dev/null)
  if [ "$SUBSCRIPTION" = "pro" ]; then
    ok "OAuth credentials 확인됨 (subscriptionType: pro)"
  else
    warn "OAuth credentials는 있으나 subscriptionType: $SUBSCRIPTION"
  fi
else
  bad "OAuth credentials 파일 없음 — VPS에서 claude 실행 후 /login 필요"
fi

# ── 3. 디스크 여유공간 ───────────────────────────────────────────────────
echo ""
echo "▶ 디스크"
DISK_LINE=$(df -h "$PROJECT_DIR" 2>/dev/null | tail -1)
DISK_PCT=$(echo "$DISK_LINE" | awk '{print $5}' | tr -d '%')
DISK_AVAIL=$(echo "$DISK_LINE" | awk '{print $4}')
if [ -n "$DISK_PCT" ]; then
  if [ "$DISK_PCT" -ge 90 ]; then
    bad "디스크 사용률 ${DISK_PCT}% (여유 ${DISK_AVAIL}) — 90% 이상, 정리 필요"
  elif [ "$DISK_PCT" -ge 75 ]; then
    warn "디스크 사용률 ${DISK_PCT}% (여유 ${DISK_AVAIL})"
  else
    ok "디스크 사용률 ${DISK_PCT}% (여유 ${DISK_AVAIL})"
  fi
else
  warn "디스크 사용률 확인 실패"
fi

# ── 4. 필수 바이너리 ─────────────────────────────────────────────────────
echo ""
echo "▶ 필수 바이너리"
for bin in ffmpeg python3 node npm git tmux; do
  if command -v "$bin" &>/dev/null; then
    ok "$bin: $(command -v "$bin")"
  else
    bad "$bin 없음"
  fi
done

# ── 5. Python 의존성 (requirements.txt) ─────────────────────────────────
echo ""
echo "▶ Python 의존성"
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
  MISSING_PY=""
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    pkg=$(echo "$line" | sed -E 's/[<>=!~].*//' | tr -d ' ')
    [ -z "$pkg" ] && continue
    python3 -c "import importlib; importlib.import_module('$pkg'.replace('-', '_'))" &>/dev/null \
      || pip3 show "$pkg" &>/dev/null \
      || MISSING_PY="$MISSING_PY $pkg"
  done < "$PROJECT_DIR/requirements.txt"
  if [ -z "$MISSING_PY" ]; then
    ok "requirements.txt 패키지 모두 설치됨"
  else
    warn "미설치 의심 패키지:$MISSING_PY (import 이름 불일치로 오탐 가능 — pip3 list로 재확인 권장)"
  fi
else
  warn "requirements.txt 없음"
fi

# ── 6. Node 의존성 + Next.js 서버 ────────────────────────────────────────
echo ""
echo "▶ Next.js 서버"
if [ -d "$PROJECT_DIR/node_modules" ]; then
  ok "node_modules 존재"
else
  bad "node_modules 없음 — npm install 필요"
fi

if curl -sf -o /dev/null -m 5 "http://localhost:3000"; then
  ok "localhost:3000 응답 있음"
else
  warn "localhost:3000 응답 없음 — suno-server 창 확인 필요"
fi

# ── 7. git 상태 ──────────────────────────────────────────────────────────
echo ""
echo "▶ Git 저장소"
cd "$PROJECT_DIR" 2>/dev/null || bad "$PROJECT_DIR 접근 불가"
if [ -d "$PROJECT_DIR/.git" ]; then
  BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
  if [ "$BEHIND" = "0" ]; then
    ok "origin/main과 동일 (뒤처짐 없음)"
  else
    warn "origin/main보다 ${BEHIND}커밋 뒤처짐 — git pull 권장"
  fi
  if [ "$DIRTY" -eq 0 ]; then
    ok "워킹트리 깨끗함"
  else
    warn "커밋되지 않은 변경 ${DIRTY}건 (VPS에서 직접 수정된 파일일 수 있음)"
  fi
fi

# ── 결과 요약 ─────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then
  echo "  ❌ 점검 실패 항목 ${FAIL}건, 경고 ${WARN}건 — 조치 후 파이프라인 시작 권장"
  echo "════════════════════════════════════════════════"
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo "  ⚠  경고 ${WARN}건 — 상황에 따라 진행 가능"
  echo "════════════════════════════════════════════════"
  exit 0
else
  echo "  ✅ 모든 점검 통과 — 파이프라인 시작 가능"
  echo "════════════════════════════════════════════════"
  exit 0
fi
