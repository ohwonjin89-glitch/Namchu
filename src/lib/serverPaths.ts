/**
 * 서버 배포 환경별 파일 경로 공용 헬퍼.
 *
 * 이 프로젝트는 원래 Windows 네이티브(D:\AI Agent\Claude\...)에서만 운영되다가
 * RunPod(/workspace/suno-api) → VPS(/home/dgm/suno-api)로 서버가 바뀌어왔다.
 * 배포 서버가 바뀔 때마다 여러 route.ts에 흩어진 하드코딩 경로를 일일이 찾아
 * 고치는 대신, PROJECT_DIR 환경변수(없으면 최신 VPS 기본값)로 한 곳에서 관리한다.
 */
import * as path from 'path';

export const IS_WINDOWS = process.platform === 'win32';

/** Linux 계열(WSL/RunPod/VPS) 배포에서 이 프로젝트의 루트 디렉토리. */
export function getProjectDir(): string {
  return process.env.PROJECT_DIR || '/home/dgm/suno-api';
}

/**
 * Windows에서의 작업 베이스(D:\AI Agent\Claude)에 대응하는 경로.
 * Windows면 그대로, Linux 계열이면 PROJECT_DIR을 반환한다.
 */
export function getWorkBase(): string {
  return IS_WINDOWS ? 'D:\\AI Agent\\Claude' : getProjectDir();
}

/** channels/ 폴더 (배경 영상·오디오 스펙트럼 업로드 등 채널별 리소스). */
export function getChannelsBase(): string {
  return IS_WINDOWS
    ? 'D:\\AI Agent\\Claude\\channels'
    : path.join(getProjectDir(), 'channels');
}
