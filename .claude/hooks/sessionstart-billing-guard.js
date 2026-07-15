#!/usr/bin/env node
// SessionStart 훅 — ANTHROPIC_API_KEY가 설정된 채 세션이 시작되면 즉시 경고를 컨텍스트에 주입한다.
// PreToolUse 가드(pretooluse-bash-guard.js)는 claude를 "새로 실행"하는 명령만 잡을 수 있으므로,
// 이미 그 상태로 시작된 세션 자체(예: VPS orchestrator pane)를 잡으려면 SessionStart가 필요하다.

if (process.env.ANTHROPIC_API_KEY) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext:
          '⚠️ 이 세션은 ANTHROPIC_API_KEY 환경변수가 설정된 채로 시작되었습니다. ' +
          'VPS orchestrator를 포함해 Claude Pro 구독으로 운영해야 하는 세션이라면, ' +
          'ANTHROPIC_API_KEY가 OAuth보다 우선되어 토큰당 과금됩니다 (2026-07-04 26M 토큰 소진 사고). ' +
          '의도적으로 API 키 과금을 쓰는 세션(generate-prompts 등 단발 라우트 호출)이 아니라면 ' +
          '이 변수를 unset 하고 /login으로 OAuth 재인증하세요.',
      },
    })
  );
}
process.exit(0);
