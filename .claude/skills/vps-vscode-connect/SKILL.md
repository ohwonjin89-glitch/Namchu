---
name: vps-vscode-connect
description: OVH VPS(51.222.9.113)의 dgm tmux 세션에 VS Code 통합 터미널(PowerShell)에서 SSH로 접속한다. "VPS 접속", "VPS 들어가", "dgm 세션 붙어", "vscode에서 vps" 같은 요청에 사용.
---

VS Code 통합 터미널(PowerShell)에서 OVH VPS(51.222.9.113)의 dgm tmux 세션에 접속한다. 매번 여러 줄 치는 게 귀찮아서 SSH config 별칭(`~/.ssh/config`, Host `dgm-vps*`)으로 한 줄로 줄여놨다.

**비밀번호는 필요 없다.** SSH 키(`C:\ssh\vps2`)만으로 인증되며, `BatchMode=yes`로 실제 확인 완료(2026-07-15). 예전에 접속 시 비밀번호를 입력하던 건 키 인증이 자리잡기 전 습관으로 남은 것으로 추정 — 이제는 그냥 `ssh` 명령 한 줄이면 바로 붙는다.

## 접속 절차 (한 줄)

### 세션이 이미 살아있을 때 (대부분의 경우)
```powershell
ssh dgm-vps-attach
```
→ 바로 dgm tmux 세션에 attach된다. 비밀번호 프롬프트 없음.

### 세션이 꺼져있어서 재생성/복구가 필요할 때
```powershell
ssh dgm-vps-setup
```
→ `sudo -u dgm bash -c 'cd /home/dgm/suno-api && bash agents/setup-vps.sh'`를 바로 실행한다. 완료 후 `ssh dgm-vps-attach`로 들어간다.

**⚠️ 세션이 살아있는데 `dgm-vps-setup`을 실행하면 안 된다** — 세션이 죽고 재생성되면서 진행 중이던 파이프라인/대화 컨텍스트가 유실된다. 반드시 세션 생사부터 확인 후 죽어있을 때만 사용한다 (`/vps-tmux-connect` 스킬 참고, 또는 아래 일반 접속으로 `tmux has-session -t dgm` 먼저 확인).

### 일반 로그인(셸만 필요할 때)
```powershell
ssh dgm-vps
```

## 참고
- tmux 창 이동: `Ctrl+b w` | orchestrator 창 바로가기: `Ctrl+b 2`
- 세션 상태를 먼저 비대화형으로 점검하고 싶다면 `/vps-tmux-connect` 스킬을 사용한다.
- 별칭 정의 위치: `C:\Users\오원진\.ssh\config` (Host `dgm-vps`, `dgm-vps-attach`, `dgm-vps-setup`)
