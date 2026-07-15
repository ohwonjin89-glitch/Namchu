#!/usr/bin/env node
// PreToolUse(Write|Edit) 가드 — 퍼블릭 레포(ohwonjin89-glitch/Namchu)에 비밀정보가
// 커밋 가능한 파일로 새로 쓰이는 것을 막는다.
// 2026-07-15 사고: /vps-vscode-connect 스킬 초안에 VPS 비밀번호를 평문으로 적었다가
// .gitignore 확인 없이 커밋될 뻔함 (feedback-vps-ssh-orchestrator.md 7번 참고).

const { execFileSync } = require('child_process');

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const filePath = input?.tool_input?.file_path;
  const content = input?.tool_input?.content ?? input?.tool_input?.new_string ?? '';
  if (!filePath || !content) process.exit(0);

  const secretPattern = /(password|passwd|secret|api[_-]?key|access[_-]?key|private[_-]?key)\s*[:=]\s*['"]?[^\s'"]{4,}/i;
  if (!secretPattern.test(content)) process.exit(0);

  try {
    execFileSync('git', ['check-ignore', '-q', filePath], { cwd: process.cwd() });
    // exit 0 = 이미 gitignore 대상 → 안전, 통과
    process.exit(0);
  } catch (e) {
    if (e.status === 1) {
      // gitignore 대상이 아님 → 퍼블릭 레포에 비밀정보가 그대로 커밋될 수 있음
      console.error(
        `[하네스 가드] ${filePath} 에 비밀정보로 보이는 문자열이 감지되었는데, 이 경로는 .gitignore 대상이 아닙니다.\n` +
        '이 저장소(ohwonjin89-glitch/Namchu)는 퍼블릭입니다. 커밋 전에 반드시:\n' +
        '  1. 실제로 비밀정보가 맞는지 확인\n' +
        '  2. 맞다면 .gitignore에 경로 추가 후 다시 시도\n' +
        '  3. 오탐(예: 변수명만 secret인 코드)이면 그대로 진행해도 무방'
      );
      process.exit(2);
    }
    // git 저장소가 아니거나 check-ignore 자체가 실패 → 판단 불가, 통과시킨다
    process.exit(0);
  }
});
