import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

// WSL(Linux 게스트) 안에서 이 dev 서버가 실행 중인지 감지한다.
// 이 프로젝트는 Next.js가 Windows 네이티브에서 실행되고, 필요 시 `wsl --`로
// WSL 안의 Python을 호출하는 구조로 설계되어 있다 (run-pipeline/route.ts 참고).
// 반대로 Next.js 자체가 WSL 안에서 실행되면 D:\, C:\Users\... 등
// Windows 전용 경로/명령을 찾지 못해 spawn이 즉시 ENOENT로 실패한다.
function isRunningInsideWSL(): boolean {
  if (process.platform !== 'linux') return false;
  if (process.env.WSL_DISTRO_NAME) return true;
  try {
    return fs.readFileSync('/proc/version', 'utf-8').toLowerCase().includes('microsoft');
  } catch {
    return false;
  }
}

const IS_WSL = isRunningInsideWSL();

const SCRIPT_PATH = process.platform === 'win32'
  ? 'D:\\AI Agent\\Claude\\make_video.py'
  : path.join(process.env.PROJECT_DIR || '/home/dgm/suno-api', 'scripts', 'make_video.py');

export async function POST(req: NextRequest) {
  try {
    const config = await req.json();
    const { outputDir } = config;

    if (!outputDir) {
      return new NextResponse(JSON.stringify({ error: 'outputDir is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    fs.mkdirSync(outputDir, { recursive: true });

    const configPath = path.join(outputDir, '_config.json');
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');

    // 초기 상태 파일
    const statusPath = path.join(outputDir, '_status.json');
    fs.writeFileSync(
      statusPath,
      JSON.stringify({ status: 'starting', progress: 0, message: '준비 중...' }),
      'utf-8'
    );

    // 이 dev 서버가 (Windows 네이티브가 아닌) WSL 안에서 잘못 실행 중이면
    // make_video.py(D:\AI Agent\Claude\)를 절대 찾을 수 없다. spawn을 시도하는
    // 대신 즉시 에러 상태를 기록하고 재기동을 안내한다.
    if (IS_WSL) {
      const message =
        'Next.js dev 서버가 WSL(Linux) 환경에서 실행 중입니다. make_video.py(D:\\AI Agent\\Claude\\)는 ' +
        'Windows 네이티브에서만 접근 가능합니다. Windows 터미널(cmd/PowerShell)에서 c:\\suno-api 로 이동 후 ' +
        'npm run dev 로 서버를 재기동해주세요.';
      console.error('[make_video] WSL 환경 감지:', message);
      fs.writeFileSync(
        statusPath,
        JSON.stringify({ status: 'error', progress: 0, message }),
        'utf-8'
      );
      return new NextResponse(JSON.stringify({ error: message, taskId: outputDir }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    // Python 프로세스 실행
    const child = spawn('python', [SCRIPT_PATH, '--config', configPath], {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    // spawn 자체가 실패하면(ENOENT 등) 'close' 이벤트가 발생하지 않아
    // _status.json이 영원히 'starting'에 멈춘다. error 핸들러로 즉시 기록한다.
    child.on('error', (err: Error) => {
      console.error('[make_video] 프로세스 시작 실패:', err.message);
      try {
        fs.writeFileSync(
          statusPath,
          JSON.stringify({
            status: 'error',
            progress: 0,
            message: `프로세스 시작 실패: ${err.message}`,
          }),
          'utf-8'
        );
      } catch {}
    });

    child.stderr.on('data', (data: Buffer) => {
      const text = data.toString().slice(0, 300);
      if (text.trim()) console.error('[make_video]', text);
    });

    child.on('close', (code: number) => {
      try {
        const current = JSON.parse(fs.readFileSync(statusPath, 'utf-8'));
        if (current.status !== 'done' && current.status !== 'error') {
          fs.writeFileSync(
            statusPath,
            JSON.stringify({
              status: code === 0 ? 'done' : 'error',
              progress: code === 0 ? 100 : 0,
              message: code === 0 ? '완료' : `프로세스 오류 (코드: ${code})`,
            }),
            'utf-8'
          );
        }
      } catch {}
    });

    return new NextResponse(JSON.stringify({ taskId: outputDir }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const taskId = url.searchParams.get('taskId');

  if (!taskId) {
    return new NextResponse(JSON.stringify({ error: 'taskId required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }

  const statusPath = path.join(taskId, '_status.json');

  if (!fs.existsSync(statusPath)) {
    return new NextResponse(
      JSON.stringify({ status: 'not_found', message: '태스크를 찾을 수 없습니다.' }),
      { status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }

  try {
    const content = fs.readFileSync(statusPath, 'utf-8');
    return new NextResponse(content, {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
