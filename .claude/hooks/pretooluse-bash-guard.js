#!/usr/bin/env node
// PreToolUse(Bash) 가드 — CLAUDE.md에 문서화된 실제 사고 패턴을 실행 전에 차단한다.
// stdin: Claude Code가 넘기는 PreToolUse JSON. stdout: 필요 시 permissionDecision JSON.
// exit 0 = 허용, exit 2 = 차단(stderr가 사유).

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0); // 파싱 실패 시 통과시킨다 (가드가 세션을 막아서는 안 됨)
  }

  const command = input?.tool_input?.command || '';
  if (!command) process.exit(0);

  // 1) 2026-06-30 사고: 살아있는 orchestrator pane에 Ctrl+C/화살표 등 탐색성 키 전송 → 팀 전체 종료
  const isSendKeys = /tmux\s+send-keys/.test(command);
  const targetsOrchestrator = /orchestrator/.test(command);
  const navKeyPattern = /\b(C-c|C-d|C-z|Up|Down|Left|Right|Escape)\b/;
  if (isSendKeys && targetsOrchestrator && navKeyPattern.test(command)) {
    console.error(
      '[하네스 가드] orchestrator pane에 탐색성 키(Ctrl+C/화살표 등) 전송이 감지되어 차단했습니다.\n' +
      '2026-06-30 사고: 같은 방식으로 실행 중이던 에이전트팀 8명이 전체 종료된 적이 있습니다.\n' +
      '상태 확인은 반드시 tmux capture-pane만 사용하고, 메시지 전달은 텍스트 + C-m(Enter)만 사용하세요.\n' +
      '(.claude/commands/vps-tmux-connect.md 2단계 참고)'
    );
    process.exit(2);
  }

  // 2) 2026-07-04 사고: ANTHROPIC_API_KEY가 설정된 채로 orchestrator/claude를 실행 → OAuth 대신 토큰당 과금, 26M 토큰 소진
  const setsApiKey = /ANTHROPIC_API_KEY\s*=/.test(command);
  const runsClaude = /\bclaude\b/.test(command);
  if (setsApiKey && runsClaude) {
    console.error(
      '[하네스 가드] ANTHROPIC_API_KEY가 설정된 채로 claude를 실행하려는 명령이 감지되어 차단했습니다.\n' +
      '2026-07-04 사고: ANTHROPIC_API_KEY가 있으면 Claude Pro OAuth보다 우선되어 토큰당 과금되며, 26M 토큰이 소진된 적이 있습니다.\n' +
      'VPS orchestrator는 반드시 OAuth 로그인(/login)만으로 실행하세요. dgm.env에도 이 키가 없어야 합니다.'
    );
    process.exit(2);
  }

  // 3) model 파라미터 누락으로 인한 Opus 오스폰 방지 — 에이전트 워커/오케스트레이터 기동 커맨드인데 --model이 없음
  const looksLikeAgentLaunch =
    runsClaude && /(--dangerously-skip-permissions|--append-system-prompt-file|--print)/.test(command);
  const hasModelFlag = /--model[\s=]/.test(command);
  if (looksLikeAgentLaunch && !hasModelFlag) {
    console.error(
      '[하네스 가드] --model 파라미터 없이 claude 에이전트를 기동하려는 명령이 감지되어 차단했습니다.\n' +
      'Agent Teams(tmux 모드)는 --model 생략 시 frontmatter의 model을 무시하고 전부 Opus로 스폰되어 과금이 커진 사고가 있었습니다.\n' +
      '명시적으로 --model claude-sonnet-5 (또는 필요한 모델)을 지정하세요.'
    );
    process.exit(2);
  }

  process.exit(0);
});
