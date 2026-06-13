#!/bin/bash
# DGM 에이전트 팀 tmux 세션 초기화 스크립트
# WSL 내부에서 실행: bash /mnt/c/suno-api/agents/setup-tmux.sh
# Windows PowerShell에서 실행: wsl -e bash /mnt/c/suno-api/agents/setup-tmux.sh

SESSION="dgm-agents"
AGENTS=(orchestrator researcher strategist music-gen image-gen video-prod uploader qa-inspect qa-tester sys-dev logs)

# 기존 세션 종료 후 바로 새 세션 생성 (서버가 꺼지지 않도록 한 줄에 처리)
tmux kill-session -t "$SESSION" 2>/dev/null; tmux new-session -d -s "$SESSION" -n "${AGENTS[0]}"

# 나머지 창 추가
for win in "${AGENTS[@]:1}"; do
    tmux new-window -t "$SESSION" -n "$win"
done

# logs 창: 최신 로그 추적
tmux send-keys -t "$SESSION:logs" \
    "echo 'Waiting for pipeline log...' && while true; do LOG=\$(ls -t /home/wonjin/agents/logs/*.log 2>/dev/null | head -1); [ -n \"\$LOG\" ] && tail -f \"\$LOG\" && break; sleep 2; done" Enter

# orchestrator 창 포커스
tmux select-window -t "$SESSION:orchestrator"

echo "✅ tmux '$SESSION' 세션 준비 완료 (${#AGENTS[@]}개 창)"
echo ""
echo "접속: wsl  →  tmux attach -t $SESSION"
echo "창 이동: Ctrl+b  숫자  또는  Ctrl+b  n/p"
echo ""
tmux list-windows -t "$SESSION"
