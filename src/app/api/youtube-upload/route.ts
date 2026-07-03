import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { getPythonCommand } from '@/lib/pythonEnv';

export const dynamic = 'force-dynamic';
export const maxDuration = 600;

const SCRIPT_PATH = path.join(process.cwd(), 'scripts', 'youtube_upload.py');

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // ── upload 액션: 비동기 처리 (spawn + 즉시 응답) ──────────────
    // 690MB 업로드는 수십 분 소요 → 동기 처리 시 HTTP 타임아웃 발생
    if (body.action === 'upload') {
      const outputPath = body.outputPath as string;
      if (!outputPath) {
        return new NextResponse(
          JSON.stringify({ error: 'upload 액션에는 outputPath가 필요합니다' }),
          { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
        );
      }

      // 출력 디렉토리 생성
      const outputDir = path.dirname(outputPath);
      fs.mkdirSync(outputDir, { recursive: true });

      // 초기 상태 파일 기록
      const statusPath = path.join(outputDir, '_upload_status.json');
      fs.writeFileSync(
        statusPath,
        JSON.stringify({ status: 'running', progress: 0, message: '업로드 준비 중...' }),
        'utf-8'
      );

      // Python 프로세스를 백그라운드에 spawn
      const child = spawn(
        getPythonCommand(),
        [SCRIPT_PATH, JSON.stringify({ ...body, statusPath })],
        { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], detached: false }
      );

      // spawn 자체가 실패하면(ENOENT 등) 'close' 이벤트가 발생하지 않아
      // _upload_status.json이 영원히 'running'에 멈춘다. error 핸들러로 즉시 기록한다.
      child.on('error', (err: Error) => {
        console.error('[youtube_upload] 프로세스 시작 실패:', err.message);
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

      let childStdout = '';
      child.stdout.on('data', (d: Buffer) => { childStdout += d.toString('utf8'); });
      child.stderr.on('data', (d: Buffer) => {
        const text = d.toString().slice(0, 300);
        if (text.trim()) console.error('[youtube_upload]', text);
      });

      child.on('close', (code: number) => {
        try {
          // Python이 stdout에 결과를 출력했으면 statusPath에 반영
          if (childStdout.trim()) {
            const lines = childStdout.trim().split('\n').filter(Boolean);
            const lastLine = lines[lines.length - 1];
            try {
              const pyResult = JSON.parse(lastLine);
              if (pyResult.error) {
                fs.writeFileSync(statusPath,
                  JSON.stringify({ status: 'error', progress: 0, message: pyResult.error }),
                  'utf-8');
                return;
              }
            } catch {}
          }
          // 상태 파일이 아직 running이면 프로세스 종료 코드로 업데이트
          const current = JSON.parse(fs.readFileSync(statusPath, 'utf-8'));
          if (current.status === 'running') {
            fs.writeFileSync(
              statusPath,
              JSON.stringify({
                status: code === 0 ? 'done' : 'error',
                progress: code === 0 ? 100 : 0,
                message: code === 0 ? '업로드 완료' : `프로세스 오류 (코드: ${code})`,
              }),
              'utf-8'
            );
          }
        } catch {}
      });

      return new NextResponse(
        JSON.stringify({ status: 'running', taskId: outputDir, statusPath }),
        { status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    // ── 그 외 액션 (auth_status, auth_start 등): 기존 동기 처리 ──
    const result = await runPython(SCRIPT_PATH, JSON.stringify(body));
    return new NextResponse(JSON.stringify(result), {
      status: result.error ? 500 : 200,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

// ── 업로드 상태 조회 (GET) ────────────────────────────────────────
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const taskId = url.searchParams.get('taskId');

  if (!taskId) {
    return new NextResponse(JSON.stringify({ error: 'taskId required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }

  const statusPath = path.join(taskId, '_upload_status.json');

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

function runPython(scriptPath: string, argsJson: string): Promise<any> {
  return new Promise((resolve) => {
    const proc = spawn(getPythonCommand(), [scriptPath, argsJson], {
      env: { ...process.env },
    });

    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => (stdout += d.toString('utf8')));
    proc.stderr.on('data', (d) => (stderr += d.toString('utf8')));

    proc.on('close', (code) => {
      try {
        const lines = stdout.trim().split('\n').filter(Boolean);
        const lastLine = lines[lines.length - 1] || '{}';
        resolve(JSON.parse(lastLine));
      } catch {
        resolve({ error: stderr || `Python 오류 (exit ${code})` });
      }
    });

    proc.on('error', (err) => resolve({ error: err.message }));
  });
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
