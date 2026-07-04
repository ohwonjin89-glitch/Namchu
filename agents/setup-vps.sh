#!/bin/bash
# DGM 에이전트 tmux 세션 설정 — OVH VPS용 (Ubuntu 22.04/24.04 LTS)
# 최초 1회: bash /home/dgm/suno-api/agents/setup-vps.sh
# 이후 재시작: 동일 명령 (패키지 재설치 없이 tmux 세션만 재생성)

set -e

PROJECT_DIR="/home/dgm/suno-api"
REPO_URL="https://github.com/ohwonjin89-glitch/Namchu.git"
SESSION="dgm"
OUTPUT_BASE="$PROJECT_DIR/.claude/agents/projects"

# ── root 권한 블록 ────────────────────────────────────────────────────────
if [ "$(id -u)" -eq 0 ]; then
  echo "▶ [root] 시스템 준비 시작..."

  # 패키지 업데이트 (최초 1회만 실질적으로 동작)
  apt-get update -qq 2>/dev/null

  # 필수 패키지 설치
  for pkg in tmux git curl python3 python3-pip ffmpeg; do
    if ! command -v "$pkg" &>/dev/null 2>&1 && ! dpkg -l "$pkg" &>/dev/null 2>&1; then
      echo "  ▶ $pkg 설치 중..."
      apt-get install -y -qq "$pkg" 2>/dev/null
    fi
  done

  # Node.js 22 설치 (없으면)
  if ! command -v node &>/dev/null; then
    echo "  ▶ Node.js 22 설치 중..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - &>/dev/null
    apt-get install -y -qq nodejs &>/dev/null
    echo "  ✓ Node.js $(node --version)"
  fi

  # Chromium 헤드리스 실행에 필요한 OS 공유 라이브러리 설치 (libnss3 등)
  # music-generator의 SUNO_GEN이 rebrowser-playwright-core로 실제 Chromium을
  # 띄워 Suno.ai와 상호작용한다 — 이 라이브러리들이 없으면 브라우저 launch()
  # 자체가 "error while loading shared libraries" 로 실패한다.
  # root 권한이 필요해 이 블록(apt 설치 구간)에서 미리 처리한다.
  echo "  ▶ Chromium 헤드리스 의존성 확인/설치 중 (수 분 소요될 수 있음)..."
  npx --yes playwright install-deps chromium &>/dev/null || echo "  ⚠ playwright install-deps 실패 — 수동 확인 필요"

  # dgm 유저 생성 (없으면)
  if ! id dgm &>/dev/null; then
    useradd -m -s /bin/bash -u 1001 dgm 2>/dev/null || useradd -m -s /bin/bash dgm
    echo "  ✓ dgm 유저 생성"
  fi

  # Claude CLI 설치 (없으면)
  if ! command -v claude &>/dev/null; then
    echo "  ▶ Claude CLI 설치 중..."
    npm install -g @anthropic-ai/claude-code &>/dev/null
    echo "  ✓ Claude CLI 설치됨"
  fi

  # SSH 공개키 복원 (프로젝트 내 백업에서)
  if [ -f "$PROJECT_DIR/.ssh_setup/authorized_key" ]; then
    mkdir -p /root/.ssh
    grep -qF "$(cat "$PROJECT_DIR/.ssh_setup/authorized_key")" /root/.ssh/authorized_keys 2>/dev/null \
      || cat "$PROJECT_DIR/.ssh_setup/authorized_key" >> /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    echo "  ✓ SSH 키 확인됨"
  fi

  # ── [BILLING GUARD 1/4] API 키 제거 — Claude Pro OAuth만 사용 ──────────────
  # API 키가 dgm.env에 있으면 무조건 삭제 (API 과금 방지)
  if grep -q "ANTHROPIC_API_KEY" /home/dgm/.config/dgm.env 2>/dev/null; then
    sed -i '/ANTHROPIC_API_KEY/d' /home/dgm/.config/dgm.env
    echo "  ⚠  API 키 감지 → dgm.env에서 제거됨 (Claude Pro OAuth만 허용)"
  fi

  # Claude 인증·설정 파일 복원 (OAuth 무조건 복원)
  if [ -f "$PROJECT_DIR/.claude_auth/.credentials.json" ]; then
    mkdir -p /home/dgm/.claude
    cp "$PROJECT_DIR/.claude_auth/.credentials.json" /home/dgm/.claude/.credentials.json
    chmod 600 /home/dgm/.claude/.credentials.json
    chown dgm:dgm /home/dgm/.claude/.credentials.json
    echo "  ✓ Claude 인증 파일 복원 (OAuth — Claude Pro)"
  else
    echo "  ⚠  .claude_auth/.credentials.json 없음 → VPS에서 /login 필요"
  fi
  if [ -f "$PROJECT_DIR/.claude_auth/settings.json" ]; then
    mkdir -p /home/dgm/.claude
    cp "$PROJECT_DIR/.claude_auth/settings.json" /home/dgm/.claude/settings.json
    echo "  ✓ Claude 설정 복원"
  fi
  chown -R dgm:dgm /home/dgm/.claude 2>/dev/null || true

  # dgm이 프로젝트 디렉토리에 접근 가능하도록
  chown -R dgm:dgm /home/dgm/suno-api 2>/dev/null || true

  # /tmp/dgm 소유권
  mkdir -p /tmp/dgm && chown dgm:dgm /tmp/dgm && chmod 755 /tmp/dgm

  echo "  ✓ 시스템 준비 완료"
  echo ""

  # dgm 유저로 이 스크립트 재실행
  exec su - dgm -c "bash $PROJECT_DIR/agents/setup-vps.sh"
fi

# ── 여기서부터 dgm 유저로 실행 ──────────────────────────────────────────

# 저장소 없으면 clone, 있으면 pull
if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "▶ 저장소 clone 중..."
  mkdir -p "$(dirname "$PROJECT_DIR")"
  git clone "$REPO_URL" "$PROJECT_DIR"
  echo "  ✓ clone 완료"
else
  echo "▶ 최신 코드 동기화..."
  cd "$PROJECT_DIR" && git pull --ff-only 2>&1 | tail -3
fi

# npm 패키지 설치 (node_modules 없으면)
if [ ! -d "$PROJECT_DIR/node_modules" ]; then
  echo "▶ npm 패키지 설치 중..."
  cd "$PROJECT_DIR" && npm install --legacy-peer-deps 2>&1 | tail -5
fi

# Python 패키지 설치 (requirements.txt 기준 — 파이프라인 스크립트가 쓰는
# anthropic/google-genai/googleapiclient/Pillow 등. 최초 1회 이후에는
# pip가 알아서 스킵하므로 매번 실행해도 무해하다)
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
  echo "▶ Python 패키지 확인/설치 중..."
  # Ubuntu 23.10+/Debian 12+는 PEP 668(externally-managed-environment)로
  # 기본 pip install을 막는다 — 실패하면 --break-system-packages로 재시도
  # (--user 설치라 시스템 패키지를 깨뜨리지 않는다).
  pip3 install --user -q -r "$PROJECT_DIR/requirements.txt" 2>/tmp/dgm_pip_install.log \
    || pip3 install --user -q --break-system-packages -r "$PROJECT_DIR/requirements.txt" 2>&1 | tail -5
fi

# tmux 설정 (focus-events + xterm-256color: Agent Teams 우측 패널 표시에 필수)
grep -q 'focus-events on' "$HOME/.tmux.conf" 2>/dev/null || echo 'set -g focus-events on' >> "$HOME/.tmux.conf"
grep -q 'default-terminal' "$HOME/.tmux.conf" 2>/dev/null \
  || echo 'set -g default-terminal "xterm-256color"' >> "$HOME/.tmux.conf"
sed -i 's/set -g default-terminal.*/set -g default-terminal "xterm-256color"/' "$HOME/.tmux.conf"
tmux source-file "$HOME/.tmux.conf" 2>/dev/null || true

# 기존 세션 제거 후 재생성 (TERM 명시: SSH 환경에서 unknown으로 잡히는 버그 방지)
tmux kill-session -t "$SESSION" 2>/dev/null || true
export TERM=xterm-256color
tmux new-session -d -s "$SESSION" -x 220 -y 50 -n "control-room" -e TERM=xterm-256color

# ── Window 0: control-room ─────────────────────────────────────────────
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m╔══════════════════════════════════════════╗\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m║\033[0m  \033[1mDGM Pipeline — OVH VPS (Singapore)\033[0m    \033[96m║\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '\033[96m╚══════════════════════════════════════════╝\033[0m\n'" Enter
tmux send-keys -t "$SESSION:control-room" \
  "printf '  \033[90mCtrl+b 1 = suno-server  |  Ctrl+b 2 = orchestrator\033[0m\n\n'" Enter

# 우측: state.json 실시간 감시
tmux split-window -t "$SESSION:control-room.0" -h -l 84
tmux send-keys -t "$SESSION:control-room.1" \
  "watch -n 2 'LATEST=\$(ls -td \"$OUTPUT_BASE\"/*/state.json 2>/dev/null | head -1); [ -n \"\$LATEST\" ] && echo \"[state.json] \$(dirname \$LATEST | xargs basename)\" && echo \"\" && python3 -c \"import json; d=json.load(open(\\\"\$LATEST\\\")); [print(f\\\"  {k}: {v}\\\") for k,v in d.get(\\\"steps\\\",{}).items()]\" 2>/dev/null || echo \"대기 중...\"'" Enter

# 우측 하단: 최신 출력폴더 파일목록
tmux split-window -t "$SESSION:control-room.1" -v -l 24
tmux send-keys -t "$SESSION:control-room.2" \
  "watch -n 3 'LATEST=\$(ls -td \"$OUTPUT_BASE\"/*/  2>/dev/null | head -1); [ -n \"\$LATEST\" ] && echo \"[output] \$(basename \$LATEST)\" && echo \"\" && ls -lh \"\$LATEST\" 2>/dev/null | tail -20 || echo \"출력 폴더 없음\"'" Enter

tmux select-pane -t "$SESSION:control-room.0"

# ── Window 1: suno-server (Next.js) ────────────────────────────────────
tmux new-window -t "$SESSION" -n "suno-server"
tmux send-keys -t "$SESSION:suno-server" \
  "cd $PROJECT_DIR && echo '▶ Next.js 서버 시작...' && npm run dev 2>&1 | tee /tmp/dgm/npm-server.log" Enter

# npm 서버 기동 대기
echo "▶ Next.js 서버 기동 대기 중 (30초)..."
sleep 30

# ── Window 2: orchestrator (teammateMode: tmux — 에이전트 스폰 시 자동 패인 생성) ─

# ── [BILLING GUARD 2/4] dgm.env 정리 — API 키 완전 제거 ────────────────────
if [ -f "/home/dgm/.config/dgm.env" ]; then
  # API 키 줄 삭제 (있으면 Claude Pro 대신 API 과금됨)
  sed -i '/ANTHROPIC_API_KEY/d' /home/dgm/.config/dgm.env
  # 필수 항목 추가 (export 형식으로)
  sed -i 's/^CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=/export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=/' /home/dgm/.config/dgm.env
  grep -q 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' /home/dgm/.config/dgm.env \
    || echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> /home/dgm/.config/dgm.env
  grep -q 'export TERM=' /home/dgm/.config/dgm.env \
    || echo 'export TERM=xterm-256color' >> /home/dgm/.config/dgm.env
  echo "▶ dgm.env 확인 완료 (API 키 없음, AGENT_TEAMS=1, TERM 설정됨)"
fi

# settings.json에 teammateMode: tmux 반영 (에이전트 스폰 시 tmux 패인 자동 생성)
python3 -c "
import json, os
f = '/home/dgm/.claude/settings.json'
d = json.load(open(f)) if os.path.exists(f) else {}
d['teammateMode'] = 'tmux'
json.dump(d, open(f,'w'), indent=2)
print('  ✓ settings.json teammateMode: tmux 설정됨')
" 2>/dev/null || true

tmux new-window -t "$SESSION" -n "orchestrator"
# ── [BILLING GUARD 3/4] unset API 키 후 billing-guard 검증 → claude 실행 ───
tmux send-keys -t "$SESSION:orchestrator" \
  "unset ANTHROPIC_API_KEY && cd $PROJECT_DIR && source /home/dgm/.config/dgm.env && bash $PROJECT_DIR/agents/billing-guard.sh && claude --model claude-sonnet-4-6 --dangerously-skip-permissions --append-system-prompt-file $PROJECT_DIR/.claude/agents/orchestrator.md" Enter

# ── Window 3: logs ─────────────────────────────────────────────────────
tmux new-window -t "$SESSION" -n "logs"
tmux send-keys -t "$SESSION:logs" \
  "watch -n 1 'ls /tmp/dgm/tasks/*.log 2>/dev/null | head -5 | while read f; do echo \"=== \$(basename \$f .log) ===\"; tail -5 \$f; echo; done || echo \"로그 없음\"'" Enter

# ── Window 4: limit-watcher ────────────────────────────────────────────
tmux new-window -t "$SESSION" -n "limit-watcher"
tmux send-keys -t "$SESSION:limit-watcher" \
  "bash $PROJECT_DIR/agents/limit-watcher.sh" Enter

# ── Window 5: completion-watcher ───────────────────────────────────────
tmux new-window -t "$SESSION" -n "completion-watcher"
tmux send-keys -t "$SESSION:completion-watcher" \
  "bash $PROJECT_DIR/agents/completion-watcher.sh" Enter

tmux select-window -t "$SESSION:orchestrator"

echo ""
echo "✅  DGM Agent Teams 세션 준비 완료 (OVH VPS)"
echo ""
echo "  접속: ssh root@<서버IP>  →  tmux attach -t $SESSION"
echo ""
echo "  [0] control-room   — 파이프라인 상태 모니터"
echo "  [1] suno-server    — Next.js API (localhost:3000)"
echo "  [2] orchestrator   — Agent Teams 메인 ★ (teammateMode: tmux)"
echo "  [3] logs           — 작업 로그"
echo "  [4] limit-watcher  — 사용량 한도 자동 해제"
echo "  [5] completion-watcher — 완료 감지"
echo ""
tmux list-windows -t "$SESSION"
