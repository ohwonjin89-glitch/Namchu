---
name: vps-tmux-connect
description: OVH VPS(51.222.9.113)의 dgm tmux 세션 상태를 안전하게 점검하고 필요 시 조치한다(로그인 상태, 한도정지, 세션 부재 등). "VPS 상태 확인", "오케스트레이터 살아있어?", "파이프라인 돌고있는지" 같은 요청에 사용. 로컬 WSL용 tmux-connect와는 별개 — 실제 DGM 메인 환경은 이 VPS다.
---

OVH VPS(51.222.9.113)의 dgm tmux 세션 상태를 확인하고, 필요 시 안전하게 조치한다.
로컬 WSL용 `/tmux-connect`와는 별개다 — 실제 DGM 파이프라인 메인 환경은 이 VPS다.

## 사전 정보
- SSH 키: `C:\ssh\vps2` (Windows) = `/c/ssh/vps2` (Git Bash)
- 접속 계정: `ubuntu` (sudo 권한, root 아님) — 실제 세션은 `dgm` 리눅스 유저 소유
- SSH 커맨드 베이스:
  ```bash
  ssh -i /c/ssh/vps2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@51.222.9.113 "명령어"
  ```
- 세션명: `dgm` — 창 6개(control-room, suno-server, orchestrator★, logs, limit-watcher, completion-watcher)
- 재생성 스크립트: `/home/dgm/suno-api/agents/setup-vps.sh` (VPS에 이미 있음)

## 실행 절차

### 1단계: 세션 존재 여부 확인
```bash
ssh -i /c/ssh/vps2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@51.222.9.113 "sudo -u dgm tmux has-session -t dgm 2>&1; echo EXIT:\$?"
```
- `EXIT:0` → 세션 살아 있음 → 2단계
- `EXIT:1` (can't find session) → 세션 없음 → 4단계

### 2단계: 세션이 살아 있을 때 — orchestrator 상태 점검
**절대 `send-keys`로 화살표/Ctrl+C 등 탐색 키를 보내지 말 것.** 읽기는 `capture-pane`만 사용한다 (2026-06-30 사고: Ctrl+C 한 번에 실행 중이던 팀 8명 전체 종료됨. 이 규칙은 `.claude/hooks/pretooluse-bash-guard.js`가 코드 레벨로도 차단한다).

```bash
ssh -i /c/ssh/vps2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@51.222.9.113 "sudo -u dgm tmux list-windows -t dgm && echo '---' && sudo -u dgm tmux capture-pane -t dgm:orchestrator -p -S -15"
```

캡처된 내용에서 상태를 판별:
- **"Not logged in"** 문구가 보이면 → OAuth 세션 만료. 3단계로.
- **"Claude Pro"** 헤더 + `⏵⏵ bypass permissions on` 표시 → 정상. 아래 안내 출력하고 종료.
  ```
  ✅ VPS dgm 세션이 정상 동작 중입니다 (Claude Pro OAuth 인증됨).

  접속 방법:
    ssh -t ubuntu@51.222.9.113 "sudo -u dgm tmux attach -t dgm"
    (또는 -i /c/ssh/vps2 키 지정 필요 시 추가)
    창 이동: Ctrl+b w  |  orchestrator 바로: Ctrl+b 2
  ```
- 메뉴 화면("Stop and wait for limit to reset" 등)에 멈춰 있으면 → 사용량 한도 정지 상태. limit-watcher.sh가 자동 해제하도록 되어 있으니 잠시 후 재확인 권장. 계속 멈춰 있으면 사용자에게 보고하고, 직접 풀 경우 텍스트 `continue` + `Enter`만 전송(방향키/Ctrl 조합 금지).

### 3단계: OAuth 재로그인 필요 시
자동으로 로그인 절차를 진행하지 말고, 사용자에게 아래 절차를 안내한다 (브라우저 인증 코드 입력이 필요해 대화형이라 자동화 불가):
```
sudo -u dgm tmux send-keys -t dgm:orchestrator '/login' C-m
```
→ "Claude account with subscription" 선택 → 표시된 URL을 브라우저에서 열고 코드 확인 → 코드를 터미널에 붙여넣고 Enter → "Logged in as ..." 확인.

**주의:** `ANTHROPIC_API_KEY` 환경변수가 설정되어 있으면 OAuth보다 우선되어 토큰당 과금된다(2026-07-04 26M 토큰 소진 사고). `dgm.env`에 해당 줄이 없는지 먼저 확인:
```bash
ssh -i /c/ssh/vps2 ... ubuntu@51.222.9.113 "cat /home/dgm/.config/dgm.env"
```

### 4단계: 세션이 꺼져 있을 때
세션이 없으므로 재생성해도 잃을 작업이 없다. 바로 진행 가능하지만, 실행 전 사용자에게 한 줄로 알리고 진행한다 (수 분 소요될 수 있음 — apt 패키지·Chromium 의존성 확인 포함).
```bash
ssh -i /c/ssh/vps2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@51.222.9.113 "sudo bash /home/dgm/suno-api/agents/setup-vps.sh"
```
완료 후 확인:
```bash
ssh -i /c/ssh/vps2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@51.222.9.113 "sudo -u dgm tmux list-windows -t dgm"
```
성공하면 2단계로 돌아가 orchestrator 로그인 상태까지 확인한다.

### ⚠️ 절대 하지 말아야 할 것
- 세션이 **살아있는데** `setup-vps.sh`를 실행하는 것 (session kill 후 재생성 → 진행 중이던 파이프라인/대화 컨텍스트 유실). 반드시 1단계에서 죽어있는 것을 확인한 뒤에만 4단계로 진행한다.
- 살아있는 orchestrator pane에 방향키·Ctrl+C 등 탐색성 키 입력 (전체 팀 종료 위험). 메시지 전달은 텍스트 + `C-m`(또는 `Enter`)만 사용.
