/**
 * Python 실행 환경 판별 유틸리티.
 *
 * 이 프로젝트는 Next.js가 Windows 네이티브에서 실행되는 것을 전제로 설계되어
 * 있다(run-pipeline/route.ts가 `wsl -- bash -c ...`로 WSL을 호출하는 구조 참고).
 * 하지만 개발 중 실수로 WSL(Linux 게스트) 안에서 dev 서버가 뜨는 경우가 있어,
 * 이를 감지하고 python 실행 커맨드를 환경에 맞게 결정하기 위한 공용 헬퍼.
 */
import * as fs from 'fs';

/** WSL(Linux 게스트) 안에서 현재 Node 프로세스가 실행 중인지 감지한다. */
export function isRunningInsideWSL(): boolean {
  if (process.platform !== 'linux') return false;
  if (process.env.WSL_DISTRO_NAME) return true;
  try {
    return fs.readFileSync('/proc/version', 'utf-8').toLowerCase().includes('microsoft');
  } catch {
    return false;
  }
}

/**
 * 이 환경에서 사용 가능한 python 실행 커맨드를 반환한다.
 * - Windows 네이티브: 'python' (PATH에 python.exe 존재)
 * - WSL / RunPod / VPS 등 Linux 계열: 'python3' (python 바이너리가 없는 경우가 대부분)
 */
export function getPythonCommand(): string {
  return process.platform === 'win32' ? 'python' : 'python3';
}
