import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { IS_WINDOWS, getChannelsBase, getProjectDir } from '@/lib/serverPaths';

export const dynamic = 'force-dynamic';

const FFMPEG_PATH    = IS_WINDOWS
  ? 'D:\\ffmpeg-8.1.1-essentials_build\\bin\\ffmpeg.exe'
  : 'ffmpeg';
// 로컬 윈도우 작업 경로와 Linux 서버(RunPod/VPS) 프로젝트 경로 둘 다 허용
const ALLOWED_BASES = IS_WINDOWS
  ? [getChannelsBase()]
  : [
      path.join(getProjectDir(), '.claude', 'agents', 'projects'),
      path.join(getProjectDir(), '.claude', 'agents', 'assets'),
    ];

function writeStatus(statusPath: string, status: string, progress: number, message: string, outputPath?: string) {
  const data: any = { status, progress, message };
  if (outputPath) data.outputPath = outputPath;
  try { fs.writeFileSync(statusPath, JSON.stringify(data, null, 2), 'utf-8'); } catch {}
}

export async function POST(req: NextRequest) {
  try {
    const { filePath, tolerance = 80 } = await req.json();

    if (!filePath) {
      return new NextResponse(JSON.stringify({ error: 'filePath가 필요합니다.' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!ALLOWED_BASES.some((base) => filePath.startsWith(base))) {
      return new NextResponse(JSON.stringify({ error: '허용되지 않는 경로입니다.' }), {
        status: 403, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!fs.existsSync(filePath)) {
      return new NextResponse(JSON.stringify({ error: '파일을 찾을 수 없습니다.' }), {
        status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const ext        = path.extname(filePath).toLowerCase();
    const baseName   = path.basename(filePath, ext);
    const dir        = path.dirname(filePath);
    const outputPath = path.join(dir, baseName + '_transparent.webm');
    const statusPath = outputPath + '.status.json';

    writeStatus(statusPath, 'running', 5, '크로마키 변환 시작...');

    const sim = Math.min(0.99, Math.max(0.01, tolerance / 255));
    const args = [
      '-y', '-i', filePath,
      '-vf', `chromakey=0x00FF00:${sim.toFixed(3)}:0.1,format=yuva420p`,
      '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '30',
      '-auto-alt-ref', '0',
      outputPath,
    ];

    const child = spawn(FFMPEG_PATH, args, {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    child.stderr.on('data', (data: Buffer) => {
      const line = data.toString();
      // FFmpeg progress 파싱 (time= 값)
      const m = line.match(/time=(\d+):(\d+):(\d+)/);
      if (m) {
        const secs = parseInt(m[1]) * 3600 + parseInt(m[2]) * 60 + parseInt(m[3]);
        writeStatus(statusPath, 'running', Math.min(90, 5 + secs / 10), `변환 중... ${m[0]}`);
      }
    });

    child.on('close', (code: number) => {
      if (code === 0) {
        writeStatus(statusPath, 'done', 100, '변환 완료!', outputPath);
      } else {
        writeStatus(statusPath, 'error', 0, `FFmpeg 오류 (코드: ${code})`);
        try { if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath); } catch {}
      }
    });

    return new NextResponse(JSON.stringify({ taskId: statusPath, outputPath }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const taskId = searchParams.get('taskId');
  if (!taskId || !fs.existsSync(taskId)) {
    return new NextResponse(JSON.stringify({ status: 'not_found' }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
  try {
    const content = fs.readFileSync(taskId, 'utf-8');
    return new NextResponse(content, {
      status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
