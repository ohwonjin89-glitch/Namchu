import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const APPDATA_BASE = path.join(
  process.env.LOCALAPPDATA || 'C:\\Users\\오원진\\AppData\\Local',
  'dgm_output'
);

const CHANNEL_FOLDER_MAP: Record<string, string> = {
  DGM: 'DGM_Playlist',
};

function getProjectsDir(channel: string): string {
  const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
  return path.join(APPDATA_BASE, chFolder, 'projects');
}

function getLatestRun(projectsDir: string): { runId: string; stateFile: string } | null {
  if (!fs.existsSync(projectsDir)) return null;

  const entries = fs.readdirSync(projectsDir, { withFileTypes: true })
    .filter(e => e.isDirectory() && !e.name.startsWith('_tmp'))
    .map(e => ({
      name: e.name,
      stateFile: path.join(projectsDir, e.name, 'state.json'),
      mtime: (() => {
        try { return fs.statSync(path.join(projectsDir, e.name, 'state.json')).mtime.getTime(); }
        catch { return 0; }
      })(),
    }))
    .filter(e => e.mtime > 0)
    .sort((a, b) => b.mtime - a.mtime);

  if (!entries.length) return null;
  return { runId: entries[0].name, stateFile: entries[0].stateFile };
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const channel = searchParams.get('channel') || 'DGM';
    const runId = searchParams.get('runId');

    const projectsDir = getProjectsDir(channel);

    let stateFile: string;
    let resolvedRunId: string;

    if (runId) {
      stateFile = path.join(projectsDir, runId, 'state.json');
      resolvedRunId = runId;
    } else {
      // 최신 run 자동 탐색
      const latest = getLatestRun(projectsDir);
      if (!latest) {
        return NextResponse.json({ error: '완료된 run 없음' }, { status: 404, headers: corsHeaders });
      }
      stateFile = latest.stateFile;
      resolvedRunId = latest.runId;
    }

    if (!fs.existsSync(stateFile)) {
      return NextResponse.json({ error: 'state.json 없음', runId: resolvedRunId }, { status: 404, headers: corsHeaders });
    }

    const state = JSON.parse(fs.readFileSync(stateFile, 'utf-8'));

    // 이미지/영상 URL 추가 (대시보드 미리보기용)
    const runDir = path.dirname(stateFile);
    const imageCandidates = [
      path.join(runDir, 'image', 'background.jpg'),
      path.join(runDir, 'image', 'background.png'),
      path.join(runDir, 'background.jpg'),
    ];
    const hasImage = imageCandidates.some(p => fs.existsSync(p));

    const videoCandidates = fs.readdirSync(runDir).filter(f => f.endsWith('.mp4'));
    const videoInSubdir = fs.existsSync(path.join(runDir, 'video'))
      ? fs.readdirSync(path.join(runDir, 'video')).filter(f => f.endsWith('.mp4'))
      : [];

    return NextResponse.json({
      runId: resolvedRunId,
      channel,
      state,
      meta: {
        hasImage,
        hasVideo: videoCandidates.length > 0 || videoInSubdir.length > 0,
        imageUrl: hasImage ? `/api/dgm/image?channel=${channel}&runId=${resolvedRunId}` : null,
      },
    }, { headers: corsHeaders });

  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}
