import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

const SCRIPT_PATH = process.platform === 'win32'
  ? 'D:\\AI Agent\\Claude\\make_video.py'
  : '/workspace/suno-api/scripts/make_video.py';

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

    // Python 프로세스 실행
    const child = spawn('python', [SCRIPT_PATH, '--config', configPath], {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
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
