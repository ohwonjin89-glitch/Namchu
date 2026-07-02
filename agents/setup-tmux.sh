#!/bin/bash
# DGM 에이전트 tmux 세션 설정 — Claude Code Agent Teams 방식
# 실행: wsl -e bash /mnt/c/suno-api/agents/setup-tmux.sh

SESSION="dgm"
OUTPUT_BASE="/mnt/c/Users/오원진/AppData/Local/dgm_output/DGM_Playlist/projects"

# 기존 세션 제거 후 재생성
tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x 220 -y 50 -n "control-room"

# ── Window 0: control-room ──────────────────────────────────────────
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m╔══════════════════════════════════════════╗\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m║\033[0m  \033[1mDGM Pipeline  — 제어 패널\033[0m                \033[96m║\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m╚══════════════════════════════════════════╝\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '  \033[90mCtrl+b 1 = orchestrator  |  Ctrl+b w = 창 목록\033[0m\n\n'" Enter

# 우측 상단: state.json 실시간 감시
tmux split-window -t "$SESSION:control-room.0" -h -l 84
tmux send-keys -t "$SESSION:control-room.1" \
  "watch -n 2 'LATEST=\$(ls -td \"$OUTPUT_BASE\"/*/state.json 2>/dev/null | head -1); [ -n \"\$LATEST\" ] && echo \"[state.json] \$(dirname \$LATEST | xargs basename)\" && echo \"\" && python3 -c \"import json; d=json.load(open(\\\"\$LATEST\\\")); [print(f\\\"  {k}: {v}\\\") for k,v in d.get(\\\"steps\\\",{}).items()]\" 2>/dev/null || echo \"대기 중...\"'" Enter

# 우측 하단: 최신 출력폴더 파일목록
tmux split-window -t "$SESSION:control-room.1" -v -l 24
tmux send-keys -t "$SESSION:control-room.2" \
  "watch -n 3 'LATEST=\$(ls -td \"$OUTPUT_BASE\"/*/  2>/dev/null | head -1); [ -n \"\$LATEST\" ] && echo \"[output] \$(basename \$LATEST)\" && echo \"\" && ls -lh \"\$LATEST\" 2>/dev/null | tail -20 || echo \"출력 폴더 없음\"'" Enter

tmux select-pane -t "$SESSION:control-room.0"

# ── Window 1: orchestrator ──────────────────────────────────────────
tmux new-window -t "$SESSION" -n "orchestrator"
tmux send-keys -t "$SESSION:orchestrator" \
  "cd /mnt/c/suno-api && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions --append-system-prompt-file /mnt/c/suno-api/.claude/agents/orchestrator.md" Enter

# ── Window 2: logs ──────────────────────────────────────────────────
tmux new-window -t "$SESSION" -n "logs"
tmux send-keys -t "$SESSION:logs" \
  "watch -n 1 'ls /tmp/dgm/tasks/*.log 2>/dev/null | head -5 | while read f; do echo \"=== \$(basename \$f .log) ===\"; tail -5 \$f; echo; done || echo \"로그 없음\"'" Enter

# ── Window 3: limit-watcher ──────────────────────────────────────────
# Agent Teams pane이 Claude 사용량 한도("What do you want to do?") 메뉴에서
# 멈춰있으면 자동으로 감지해 Enter로 "한도 복구 대기"를 확정해 재개시킨다.
tmux new-window -t "$SESSION" -n "limit-watcher"
tmux send-keys -t "$SESSION:limit-watcher" \
  "bash /mnt/c/suno-api/agents/limit-watcher.sh" Enter

tmux select-window -t "$SESSION:orchestrator"

echo ""
echo "✅  DGM Agent Teams 세션 준비 완료"
echo "     CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 활성화됨"
echo ""
echo "  접속:  wsl  →  tmux attach -t $SESSION"
echo ""
echo "  [0] control-room   — 파이프라인 상태"
echo "  [1] orchestrator   — Agent Teams 메인 (★)"
echo "  [2] logs           — 작업 로그"
echo "  [3] limit-watcher  — 사용량 한도 메뉴 자동 해제"
echo ""
tmux list-windows -t "$SESSION"
