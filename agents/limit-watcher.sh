#!/bin/bash
# 사용량 한도("What do you want to do?") 메뉴에 멈춰있는 Agent Teams pane을 자동 감지/해제
# 실행: wsl -e bash /mnt/c/suno-api/agents/limit-watcher.sh
# (보통은 setup-tmux.sh가 dgm 세션의 별도 창으로 자동 기동한다)
#
# Claude Code는 "Stop and wait for limit to reset"을 선택해도 한도가 풀리는 시점을
# 자동으로 감지해 작업을 재개하지 않는다 (CLI 자체의 미구현 기능 — GitHub 이슈
# #18980, #26775, #35744, #36320, #38263). 따라서 이 스크립트는 두 단계로 동작한다:
#   1. 메뉴 감지 시 Enter로 "Stop and wait for limit to reset" 확정
#   2. 이후 pane이 계속 idle(작업 중 표시인 "esc to interrupt"가 없음)이면
#      일정 간격으로 "continue"를 보내 재개를 시도한다 (한도가 안 풀렸으면
#      그냥 같은 메뉴가 다시 뜨거나 무시되고, 풀렸으면 실제로 재개된다)

SESSION="dgm"
WINDOW="orchestrator"
INTERVAL=30
CONTINUE_RETRY=180   # 한도 대기 중 'continue' 재시도 간격(초) — 너무 잦으면 로그/대화 스팸
LOG="/tmp/dgm/limit-watcher.log"

mkdir -p /tmp/dgm
declare -A WAITING
declare -A LAST_TRY

echo "[limit-watcher] 시작 — ${SESSION}:${WINDOW} 의 모든 pane을 ${INTERVAL}초 간격으로 감시"

while true; do
  NOW=$(date +%s)
  PANES=$(tmux list-panes -t "${SESSION}:${WINDOW}" -F '#{pane_index}' 2>/dev/null)
  for p in $PANES; do
    CONTENT=$(tmux capture-pane -t "${SESSION}:${WINDOW}.${p}" -p -S -15 2>/dev/null)
    TS=$(date '+%Y-%m-%d %H:%M:%S')

    if echo "$CONTENT" | grep -q "What do you want to do?"; then
      echo "[$TS] pane ${p}: 한도 메뉴 감지 → Enter로 '복구 대기' 확정" | tee -a "$LOG"
      tmux send-keys -t "${SESSION}:${WINDOW}.${p}" Enter
      WAITING[$p]=1
      LAST_TRY[$p]=0
      continue
    fi

    # API 키 rate limit: overloaded_error 또는 529 감지 → 60초 대기 후 continue
    if echo "$CONTENT" | grep -qE "overloaded_error|529|rate.limit|Too many requests"; then
      LAST=${LAST_TRY[$p]:-0}
      if [ $((NOW - LAST)) -ge 60 ]; then
        echo "[$TS] pane ${p}: API rate limit 감지 → 60초 후 continue 전송" | tee -a "$LOG"
        sleep 60
        tmux send-keys -t "${SESSION}:${WINDOW}.${p}" "continue" Enter
        LAST_TRY[$p]=$NOW
      fi
      continue
    fi

    if [ "${WAITING[$p]}" = "1" ]; then
      if echo "$CONTENT" | grep -q "esc to interrupt"; then
        echo "[$TS] pane ${p}: 작업 재개 확인 → 감시 해제" | tee -a "$LOG"
        unset WAITING[$p]
        unset LAST_TRY[$p]
      else
        LAST=${LAST_TRY[$p]:-0}
        if [ $((NOW - LAST)) -ge "$CONTINUE_RETRY" ]; then
          echo "[$TS] pane ${p}: 한도 대기 중 추정 → 'continue' 전송 시도" | tee -a "$LOG"
          tmux send-keys -t "${SESSION}:${WINDOW}.${p}" "continue" Enter
          LAST_TRY[$p]=$NOW
        fi
      fi
    fi
  done
  sleep "$INTERVAL"
done
