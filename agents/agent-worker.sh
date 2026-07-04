#!/bin/bash
# DGM 에이전트 워커 — 파일 기반 태스크 큐 폴링
# 사용법: bash agent-worker.sh <agent-name>

AGENT_NAME="${1:-unknown}"
TASK_DIR="/tmp/dgm/tasks"
AGENT_MD="/home/dgm/suno-api/.claude/agents/${AGENT_NAME}.md"
TASK_FILE="${TASK_DIR}/${AGENT_NAME}.task"
RESULT_FILE="${TASK_DIR}/${AGENT_NAME}.result"
LOG_FILE="${TASK_DIR}/${AGENT_NAME}.log"

mkdir -p "$TASK_DIR"

# API 키
if [ -z "$ANTHROPIC_API_KEY" ] && [ -f "/home/dgm/.config/dgm.env" ]; then
    source /home/dgm/.config/dgm.env
fi

# 시스템 프롬프트 로드
SYSTEM_PROMPT="당신은 ${AGENT_NAME} 에이전트입니다."
if [ -f "$AGENT_MD" ]; then
    SYSTEM_PROMPT=$(python3 -c "
text = open('$AGENT_MD', encoding='utf-8').read()
if text.startswith('---'):
    end = text.find('---', 3)
    text = text[end+3:].lstrip('\n') if end != -1 else text
print(text)
" 2>/dev/null)
fi

echo "[${AGENT_NAME}] 대기 중..."

# ── 메인 루프 ─────────────────────────────────────────────────────
while true; do
    if [ -f "$TASK_FILE" ]; then
        TASK=$(cat "$TASK_FILE")
        rm -f "$TASK_FILE" "$RESULT_FILE"
        TS=$(date '+%H:%M:%S')
        echo "[${AGENT_NAME}] 작업 수신 [$TS]"

        RESULT=$(claude --print \
            --model claude-sonnet-4-6 \
            --system-prompt "$SYSTEM_PROMPT" \
            --dangerously-skip-permissions \
            "$TASK" 2>&1)
        CODE=$?
        DONE=$(date '+%H:%M:%S')

        if [ $CODE -eq 0 ]; then
            printf '%s\n__DONE__\n' "$RESULT" > "$RESULT_FILE"
            echo "[${AGENT_NAME}] 완료 [$DONE]"
        else
            printf 'ERROR: %s\n__DONE__\n' "$RESULT" > "$RESULT_FILE"
            echo "[${AGENT_NAME}] 오류: ${RESULT:0:100}"
        fi

        {
            echo "=== $TS → $DONE ==="
            echo "TASK: ${TASK:0:200}"
            echo "RESULT: ${RESULT:0:500}"
            echo ""
        } >> "$LOG_FILE"

        echo "[${AGENT_NAME}] 대기 중..."
    fi
    sleep 1
done
