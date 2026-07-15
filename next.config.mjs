/** @type {import('next').NextConfig} */
const nextConfig = {
  // next start(플레인 Node 서버)로만 배포하므로 서버리스 번들용 파일 트레이싱이 불필요.
  // 트레이싱을 켜두면 코드 안의 절대경로 문자열(예: D:\AI Agent\Claude, PROJECT_DIR 등)을
  // 정적 분석으로 스캔하다가 그 아래 실제 대용량 미디어 트리까지 훑고, exFAT 드라이브에서는
  // readlink가 EISDIR을 던져 빌드 자체가 죽는 문제가 있어 꺼둔다.
  outputFileTracing: false,
  webpack: (config) => {
    config.module.rules.push({
      test: /\.(ttf|html)$/i,
      type: 'asset/resource'
    });
    return config;
  },
  experimental: {
    serverMinification: false, // the server minification unfortunately breaks the selector class names
  },
};  

export default nextConfig;
