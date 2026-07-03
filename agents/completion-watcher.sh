#!/bin/bash
# 파이프라인 완료 또는 장기 중단 감지 → tmux 창에 알림 표시
# 실행: setup-vps.sh 또는 setup-tmux-server.sh가 별도 창으로 자동 기동
#
# 감지 조건:
#   1. qa-inspector가 meeting_log.md에 기록 완료 → 정상 완료
#   2. meeting_log.md가 TIMEOUT_HOURS 이상 변경 없음 → 비정상 중단 가능성
#   3. orchestrator pane에 claude 프로세스 없음 → 종료 감지

# 프로젝트 경로: VPS는 /home/dgm, RunPod은 /workspace
if [ -d "/home/dgm/suno-api" ]; then
  OUTPUT_BASE="/home/dgm/suno-api/.claude/agents/projects"
  ENV_FILE="/home/dgm/suno-api/.env"
else
  OUTPUT_BASE="/workspace/suno-api/.claude/agents/projects"
  ENV_FILE="/workspace/suno-api/.env"
fi
LOG="/tmp/dgm/completion-watcher.log"
CHECK_INTERVAL=60      # 점검 주기 (초)
TIMEOUT_HOURS=4        # 이 시간 이상 진행 없으면 강제 종료 (토큰한도 대기 포함)
SESSION="dgm"

mkdir -p /tmp/dgm

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

notify_done() {
  local reason="$1"
  log "✅ 파이프라인 종료: $reason"
  # tmux control-room 창에 완료 배너 표시
  tmux send-keys -t "${SESSION}:control-room.0" "" ""
  tmux display-message -t "$SESSION" "DGM 파이프라인 완료: $reason"
}

log "completion-watcher 시작 (종료 기준: qa-inspector 완료 또는 ${TIMEOUT_HOURS}시간 무진행)"

LAST_PROGRESS_TIME=$(date +%s)
PREV_LOG_MTIME=0

while true; do
  sleep "$CHECK_INTERVAL"
  NOW=$(date +%s)

  # 최신 프로젝트 finding
  LATEST_PROJECT=$(ls -td "$OUTPUT_BASE"/*/  2>/dev/null | head -1)
  if [ -z "$LATEST_PROJECT" ]; then
    continue
  fi

  MEETING_LOG="${LATEST_PROJECT}meeting_log.md"
  if [ ! -f "$MEETING_LOG" ]; then
    continue
  fi

  # meeting_log 마지막 수정 시간 체크
  if command -v stat &>/dev/null; then
    MTIME=$(stat -c %Y "$MEETING_LOG" 2>/dev/null || echo 0)
  else
    MTIME=0
  fi

  if [ "$MTIME" -ne "$PREV_LOG_MTIME" ]; then
    LAST_PROGRESS_TIME=$NOW
    PREV_LOG_MTIME=$MTIME
  fi

  # 조건 1: qa-inspector 완료 감지
  if grep -q "^## qa-inspector" "$MEETING_LOG" 2>/dev/null; then
    log "✅ qa-inspector 완료 감지 — 파이프라인 정상 종료"
    sleep 30  # 최종 파일 기록 완료 대기
    notify_done "파이프라인 정상 완료"
    exit 0
  fi

  # 조건 2: 타임아웃 (진행 없음)
  IDLE_SECONDS=$(( NOW - LAST_PROGRESS_TIME ))
  IDLE_HOURS=$(( IDLE_SECONDS / 3600 ))
  if [ "$IDLE_HOURS" -ge "$TIMEOUT_HOURS" ]; then
    log "⏰ ${TIMEOUT_HOURS}시간 이상 무진행 (마지막 진행: ${IDLE_SECONDS}초 전) → 강제 종료"
    notify_done "타임아웃 (${TIMEOUT_HOURS}h 무진행 — orchestrator 확인 필요)"
    exit 1
  fi

  # 조건 3: orchestrator claude 프로세스 없음
  CLAUDE_RUNNING=$(tmux capture-pane -t "${SESSION}:orchestrator" -p -S -3 2>/dev/null | grep -c "esc to interrupt\|Choreographing\|↓.*tokens" || true)
  if [ "$CLAUDE_RUNNING" -eq 0 ]; then
    # claude가 없으면 한 번 더 기다린 후 재확인
    sleep 30
    CLAUDE_RUNNING2=$(tmux capture-pane -t "${SESSION}:orchestrator" -p -S -3 2>/dev/null | grep -c "esc to interrupt\|Choreographing\|↓.*tokens" || true)
    if [ "$CLAUDE_RUNNING2" -eq 0 ]; then
      log "⚠ orchestrator claude 프로세스 종료 감지 — 1시간 추가 대기 후 pod 종료"
      sleep 3600
      notify_done "orchestrator claude 프로세스 종료 감지"
      exit 1
    fi
  fi

  # 주기적 상태 로그 (30분마다)
  if [ $(( IDLE_SECONDS % 1800 )) -lt "$CHECK_INTERVAL" ]; then
    log "상태: 진행 중 (마지막 변경: ${IDLE_SECONDS}초 전, ${IDLE_HOURS}h/${TIMEOUT_HOURS}h)"
  fi
done
