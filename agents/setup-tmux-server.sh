#!/bin/bash
# DGM 에이전트 tmux 세션 설정 — RunPod 서버용 (네이티브 Linux, WSL 경로 없음)
# 실행: bash /workspace/suno-api/agents/setup-tmux-server.sh
# root 또는 dgm 유저 모두에서 실행 가능. root일 경우 dgm 유저로 전환 후 tmux 실행.

PROJECT_DIR="/workspace/suno-api"
SESSION="dgm"
OUTPUT_BASE="$PROJECT_DIR/.claude/agents/projects"

# ── root 권한 블록: dgm 유저·node·claude 준비 ──────────────────────────
if [ "$(id -u)" -eq 0 ]; then
  echo "▶ [root] 사전 준비 시작..."

  # SSH 키 복원
  if [ -f "$PROJECT_DIR/.ssh_setup/authorized_key" ]; then
    mkdir -p /root/.ssh
    cat "$PROJECT_DIR/.ssh_setup/authorized_key" >> /root/.ssh/authorized_keys
    sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    echo "  ✓ SSH 키 복원됨"
  fi

  # dgm 유저 생성 (없으면)
  if ! id dgm &>/dev/null; then
    useradd -m -s /bin/bash -u 1001 dgm 2>/dev/null || useradd -m -s /bin/bash dgm
    echo "  ✓ dgm 유저 생성됨"
  fi

  # Node.js 설치 (없으면)
  if ! command -v node &>/dev/null; then
    echo "  ▶ Node.js 설치 중..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - &>/dev/null
    apt-get install -y nodejs &>/dev/null
    echo "  ✓ Node.js $(node --version) 설치됨"
  fi

  # claude CLI 설치 (없으면)
  if ! command -v claude &>/dev/null; then
    echo "  ▶ claude CLI 설치 중..."
    npm install -g @anthropic-ai/claude-code &>/dev/null
    echo "  ✓ claude $(claude --version 2>/dev/null | head -1) 설치됨"
  fi

  # claude 인증·설정 파일 복원 (workspace 백업에서)
  if [ -f "$PROJECT_DIR/.claude_auth/.credentials.json" ]; then
    mkdir -p /home/dgm/.claude
    cp "$PROJECT_DIR/.claude_auth/.credentials.json" /home/dgm/.claude/.credentials.json
    chmod 600 /home/dgm/.claude/.credentials.json
    echo "  ✓ claude 인증 파일 복원됨 (Claude Pro OAuth)"
  fi
  if [ -f "$PROJECT_DIR/.claude_auth/settings.json" ]; then
    mkdir -p /home/dgm/.claude
    cp "$PROJECT_DIR/.claude_auth/settings.json" /home/dgm/.claude/settings.json
    echo "  ✓ claude 설정 복원됨 (테마·권한 프롬프트 스킵)"
  fi
  chown -R dgm:dgm /home/dgm/.claude 2>/dev/null

  # RUNPOD 키를 .env에 자동 주입 (없을 경우)
  # .env는 gitignore 대상이라 git pull로 안 오므로 setup 시 직접 보장
  # RunPod 대시보드 > Pod > Environment Variables 에 RUNPOD_API_KEY 설정 필요
  if ! grep -q "^RUNPOD_API_KEY=" "$PROJECT_DIR/.env" 2>/dev/null; then
    if [ -n "${RUNPOD_API_KEY:-}" ]; then
      echo "RUNPOD_API_KEY=${RUNPOD_API_KEY}" >> "$PROJECT_DIR/.env"
      echo "  ✓ RUNPOD_API_KEY(환경변수에서) → .env 주입됨"
    else
      echo "  ⚠ RUNPOD_API_KEY 없음 — RunPod 대시보드 > Pod > Env Variables에 설정 필요"
    fi
  fi
  if ! grep -q "^RUNPOD_POD_ID=" "$PROJECT_DIR/.env" 2>/dev/null; then
    if [ -n "${RUNPOD_POD_ID:-}" ]; then
      echo "RUNPOD_POD_ID=${RUNPOD_POD_ID}" >> "$PROJECT_DIR/.env"
      echo "  ✓ RUNPOD_POD_ID(환경변수에서) → .env 주입됨: ${RUNPOD_POD_ID}"
    else
      echo "  ⚠ RUNPOD_POD_ID 없음 — RunPod 대시보드 > Pod > Env Variables에 설정 필요"
    fi
  fi

  # /tmp/dgm 소유권 설정
  mkdir -p /tmp/dgm && chown dgm:dgm /tmp/dgm && chmod 755 /tmp/dgm

  # JupyterLab 숨김파일 표시 설정
  JLAB_SETTINGS="/root/.jupyter/lab/user-settings/@jupyterlab/filebrowser-extension"
  mkdir -p "$JLAB_SETTINGS"
  echo '{"showHiddenFiles": true}' > "$JLAB_SETTINGS/browser.jupyterlab-settings"

  # 프로젝트 폴더 바로가기 심볼릭 링크
  ln -sfn /workspace/suno-api/.claude/agents/projects /workspace/projects

  echo "  ✓ 사전 준비 완료"
  echo ""

  # dgm 유저로 이 스크립트 재실행
  exec su - dgm -c "bash $PROJECT_DIR/agents/setup-tmux-server.sh"
fi

# ── 여기서부터 dgm 유저로 실행 ──────────────────────────────────────────

# 최신 코드 반영 (git pull)
echo "▶ 최신 코드 동기화..."
cd "$PROJECT_DIR" && git pull --ff-only 2>&1 | tail -3 && echo "  ✓ git pull 완료"

# 기존 세션 제거 후 재생성
tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x 220 -y 50 -n "control-room"

# ── Window 0: control-room ──────────────────────────────────────────
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m╔══════════════════════════════════════════╗\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m║\033[0m  \033[1mDGM Pipeline  — 제어 패널 (서버)\033[0m         \033[96m║\033[0m\n'" Enter
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

# ── Window 1: suno-api server (Next.js) ──────────────────────────────
tmux new-window -t "$SESSION" -n "suno-server"
tmux send-keys -t "$SESSION:suno-server" \
  "cd $PROJECT_DIR && npm install --legacy-peer-deps 2>&1 | tail -3 && echo '▶ npm 서버 시작...' && npm run dev 2>&1 | tee /tmp/dgm/npm-server.log" Enter

# npm 서버가 포트 3000에 바인딩될 때까지 대기 (최대 60초)
tmux send-keys -t "$SESSION:control-room.0" \
  "echo '▶ npm 서버 포트 3000 대기 중...'" Enter
sleep 30

# ── Window 2: orchestrator ──────────────────────────────────────────
tmux new-window -t "$SESSION" -n "orchestrator"
tmux send-keys -t "$SESSION:orchestrator" \
  "cd $PROJECT_DIR && unset ANTHROPIC_API_KEY && export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && claude --dangerously-skip-permissions --append-system-prompt-file $PROJECT_DIR/.claude/agents/orchestrator.md" Enter

# ── Window 3: logs ──────────────────────────────────────────────────
tmux new-window -t "$SESSION" -n "logs"
tmux send-keys -t "$SESSION:logs" \
  "watch -n 1 'ls /tmp/dgm/tasks/*.log 2>/dev/null | head -5 | while read f; do echo \"=== \$(basename \$f .log) ===\"; tail -5 \$f; echo; done || echo \"로그 없음\"'" Enter

# ── Window 4: limit-watcher ──────────────────────────────────────────
tmux new-window -t "$SESSION" -n "limit-watcher"
tmux send-keys -t "$SESSION:limit-watcher" \
  "bash $PROJECT_DIR/agents/limit-watcher.sh" Enter

# ── Window 5: completion-watcher ──────────────────────────────────────
# qa-inspector 완료 또는 TIMEOUT_HOURS 무진행 시 RunPod pod 자동 종료
tmux new-window -t "$SESSION" -n "completion-watcher"
tmux send-keys -t "$SESSION:completion-watcher" \
  "bash $PROJECT_DIR/agents/completion-watcher.sh" Enter

tmux select-window -t "$SESSION:orchestrator"

echo ""
echo "✅  DGM Agent Teams 세션 준비 완료 (서버: $(hostname))"
echo "     CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 활성화됨"
echo ""
echo "  접속:  ssh -i ~/.ssh/runpod_dgm -p <PORT> root@<IP>  →  tmux attach -t $SESSION"
echo ""
echo "  [0] control-room     — 파이프라인 상태"
echo "  [1] suno-server      — Next.js API 서버 (localhost:3000)"
echo "  [2] orchestrator     — Agent Teams 메인 (★)"
echo "  [3] logs             — 작업 로그"
echo "  [4] limit-watcher    — 사용량 한도 메뉴 자동 해제"
echo "  [5] completion-watcher — 완료 시 pod 자동 종료"
echo ""
tmux list-windows -t "$SESSION"
