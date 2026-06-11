#!/bin/bash
# DGM Playlist 자동화 오케스트레이터
# 사용법: ./orchestrator.sh [채널명]
# 예시:  ./orchestrator.sh DGM

CHANNEL=${1:-DGM}
PROJECT_DIR="/mnt/c/suno-api"
AGENTS_DIR="/home/wonjin/agents"
LOG_DIR="/home/wonjin/agents/logs"
API_BASE="http://localhost:3000"

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_DIR/orchestrator.log"; }
fail() { log "❌ 실패: $1"; exit 1; }
ok()   { log "✅ $1"; }

# suno-api 서버 실행 중인지 확인
check_server() {
  curl -s "$API_BASE/api/get_limit" -o /dev/null -w "%{http_code}" 2>/dev/null
}

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🎵 DGM Playlist 자동화 시작 | 채널: $CHANNEL"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 서버 확인
STATUS=$(check_server)
if [ "$STATUS" != "200" ]; then
  fail "suno-api 서버가 꺼져 있습니다. Windows에서 'npm run dev' 먼저 실행하세요."
fi
ok "suno-api 서버 연결됨"

# TMUX 세션 이름
SESSION="dgm-agents"

# 기존 세션 종료
tmux kill-session -t "$SESSION" 2>/dev/null

# 새 TMUX 세션 생성 (백그라운드)
tmux new-session -d -s "$SESSION" -x 220 -y 50

# ── 창 레이아웃 ──
# 창 0: 오케스트레이터 로그
# 창 1: 트렌드 분석 에이전트
# 창 2: 프롬프트 작성 에이전트
# 창 3: 음악 생성 에이전트
# 창 4: 이미지 생성 에이전트
# 창 5: 영상 제작 에이전트
# 창 6: 업로드 에이전트

tmux rename-window -t "$SESSION:0" "orchestrator"
tmux new-window -t "$SESSION" -n "trend"
tmux new-window -t "$SESSION" -n "prompt"
tmux new-window -t "$SESSION" -n "music"
tmux new-window -t "$SESSION" -n "image"
tmux new-window -t "$SESSION" -n "video"
tmux new-window -t "$SESSION" -n "upload"

log "TMUX 세션 '$SESSION' 생성됨 (창 7개)"

# ── 상태 파일 초기화 ──
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"
cat > "$STATE_FILE" << EOF
{
  "channel": "$CHANNEL",
  "startedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "running",
  "steps": {
    "trend":   "pending",
    "prompt":  "pending",
    "music":   "pending",
    "image":   "pending",
    "video":   "pending",
    "upload":  "pending"
  }
}
EOF

log "상태 파일 초기화: $STATE_FILE"

# ── 에이전트 순차 실행 ──

# 1단계: 트렌드 분석
log "▶ [1/6] 트렌드 분석 에이전트 시작..."
tmux send-keys -t "$SESSION:trend" \
  "bash $AGENTS_DIR/agent_trend.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/trend.log" Enter

# 완료 대기 (최대 5분)
wait_for_step() {
  local STEP=$1
  local MAX=$2
  local i=0
  while [ $i -lt $MAX ]; do
    STEP_STATUS=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d['steps']['$STEP'])" 2>/dev/null)
    if [ "$STEP_STATUS" = "done" ]; then return 0; fi
    if [ "$STEP_STATUS" = "error" ]; then return 1; fi
    sleep 5
    i=$((i+5))
  done
  return 1
}

wait_for_step "trend" 300 && ok "트렌드 분석 완료" || fail "트렌드 분석 실패"

# 2단계: 프롬프트 작성
log "▶ [2/6] 프롬프트 작성 에이전트 시작..."
tmux send-keys -t "$SESSION:prompt" \
  "bash $AGENTS_DIR/agent_prompt.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/prompt.log" Enter
wait_for_step "prompt" 180 && ok "프롬프트 작성 완료" || fail "프롬프트 작성 실패"

# 3단계: 음악 생성
log "▶ [3/6] 음악 생성 에이전트 시작..."
tmux send-keys -t "$SESSION:music" \
  "bash $AGENTS_DIR/agent_music.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/music.log" Enter
wait_for_step "music" 600 && ok "음악 생성 완료" || fail "음악 생성 실패"

# 4단계: 이미지 생성
log "▶ [4/6] 이미지 생성 에이전트 시작..."
tmux send-keys -t "$SESSION:image" \
  "bash $AGENTS_DIR/agent_image.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/image.log" Enter
wait_for_step "image" 600 && ok "이미지 생성 완료" || fail "이미지 생성 실패"

# 5단계: 영상 제작
log "▶ [5/6] 영상 제작 에이전트 시작..."
tmux send-keys -t "$SESSION:video" \
  "bash $AGENTS_DIR/agent_video.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/video.log" Enter
wait_for_step "video" 900 && ok "영상 제작 완료" || fail "영상 제작 실패"

# 6단계: 업로드
log "▶ [6/6] 업로드 에이전트 시작..."
tmux send-keys -t "$SESSION:upload" \
  "bash $AGENTS_DIR/agent_upload.sh '$CHANNEL' 2>&1 | tee $LOG_DIR/upload.log" Enter
wait_for_step "upload" 300 && ok "업로드 완료" || fail "업로드 실패"

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🎉 전체 파이프라인 완료!"
log "TMUX 모니터링: tmux attach -t $SESSION"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 오케스트레이터 창에 요약 표시
tmux send-keys -t "$SESSION:orchestrator" \
  "cat $LOG_DIR/orchestrator.log" Enter
tmux select-window -t "$SESSION:orchestrator"
