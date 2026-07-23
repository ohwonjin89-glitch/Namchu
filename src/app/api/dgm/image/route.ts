import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const CHANNEL_FOLDER_MAP: Record<string, string> = {
  DGM: 'DGM_Playlist',
};

const APPDATA_BASE = path.join(
  process.env.LOCALAPPDATA || 'C:\\Users\\오원진\\AppData\\Local',
  'dgm_output'
);

const D_PROJECTS_BASE = 'D:\\AI Agent\\Claude\\channels';

function getRunDir(channel: string, runId: string): string {
  const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
  if (runId.startsWith('legacy:')) {
    return path.join(APPDATA_BASE, chFolder, runId.slice(7));
  }
  if (runId.startsWith('dprojects:')) {
    return path.join(D_PROJECTS_BASE, chFolder, 'projects', runId.slice(10));
  }
  return path.join(APPDATA_BASE, chFolder, 'projects', runId);
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const channel = searchParams.get('channel') || 'DGM';
    const runId = searchParams.get('runId');

    if (!runId) return NextResponse.json({ error: 'runId 필요' }, { status: 400 });

    const runDir = getRunDir(channel, runId);

    // image/ 서브폴더 우선, 루트 폴더 폴백
    const candidates = [
      path.join(runDir, 'image', 'background.jpg'),
      path.join(runDir, 'image', 'background.png'),
      path.join(runDir, 'background.jpg'),
      path.join(runDir, 'background.png'),
    ];

    const imgPath = candidates.find(p => fs.existsSync(p)) || null;
    if (!imgPath) return NextResponse.json({ error: '이미지 없음' }, { status: 404 });

    const ext = path.extname(imgPath).slice(1);
    const contentType = ext === 'jpg' ? 'image/jpeg' : 'image/png';
    const data = fs.readFileSync(imgPath);

    return new NextResponse(data, {
      status: 200,
      headers: { 'Content-Type': contentType, ...corsHeaders },
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
