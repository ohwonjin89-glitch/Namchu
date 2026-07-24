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

// D: 드라이브 프로젝트 경로 (구 대시보드 위치 — 읽기 전용 참조)
const D_PROJECTS_BASE = 'D:\\AI Agent\\Claude\\channels';

function getNewProjectsDir(channel: string): string {
  const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
  return path.join(APPDATA_BASE, chFolder, 'projects');
}

function getDProjectsDir(channel: string): string {
  const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
  return path.join(D_PROJECTS_BASE, chFolder, 'projects');
}

function getRunDir(channel: string, runId: string): string | null {
  if (runId.startsWith('legacy:')) {
    // 구형 타임스탬프 폴더 — AppData 채널 루트에 위치
    const legacyId = runId.slice(7);
    const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
    return path.join(APPDATA_BASE, chFolder, legacyId);
  }
  if (runId.startsWith('dprojects:')) {
    // D: 드라이브 구 대시보드 프로젝트
    const projId = runId.slice(10);
    return path.join(getDProjectsDir(channel), projId);
  }
  // 신규: AppData projects 폴더
  return path.join(getNewProjectsDir(channel), runId);
}

function listRuns(channel: string): any[] {
  const results: any[] = [];

  // ── 신규 경로: AppData/{ch}/projects/{concept}_{date}/ ──────────────
  const newProjectsDir = getNewProjectsDir(channel);
  if (fs.existsSync(newProjectsDir)) {
    const dirs = fs.readdirSync(newProjectsDir, { withFileTypes: true })
      .filter(d => d.isDirectory() && !d.name.startsWith('_tmp_'))
      .map(d => d.name);

    for (const runId of dirs) {
      const runDir = path.join(newProjectsDir, runId);
      const stateFile = path.join(runDir, 'state.json');
      if (!fs.existsSync(stateFile)) continue;

      let state: any = { date: runId, steps: {} };
      try { state = JSON.parse(fs.readFileSync(stateFile, 'utf-8')); } catch {}

      const hasImage =
        fs.existsSync(path.join(runDir, 'image', 'background.jpg')) ||
        fs.existsSync(path.join(runDir, 'image', 'background.png')) ||
        fs.existsSync(path.join(runDir, 'background.jpg')) ||
        fs.existsSync(path.join(runDir, 'background.png'));

      results.push({
        runId,
        channel,
        status: state.status || 'unknown',
        uploadedUrl: state.uploadedUrl || null,
        uploadTitle: state.stepData?.upload?.title || state.uploadTitle || null,
        startedAt: state.startedAt || null,
        completedAt: state.completedAt || null,
        steps: state.steps || {},
        hasImage,
        source: 'projects',
      });
    }
  }

  // ── 레거시: AppData/{ch}/{timestamp}/ (구형 실행 기록) ──────────────
  const chFolder = CHANNEL_FOLDER_MAP[channel] || channel;
  const legacyDir = path.join(APPDATA_BASE, chFolder);
  if (fs.existsSync(legacyDir)) {
    const legacyDirs = fs.readdirSync(legacyDir)
      .filter(d => /^\d{8}_\d{6}$/.test(d))
      .sort().reverse().slice(0, 5);

    for (const legacyId of legacyDirs) {
      const runDir = path.join(legacyDir, legacyId);
      const stateFile = path.join(runDir, 'state.json');
      let state: any = { date: legacyId, steps: {} };
      if (fs.existsSync(stateFile)) {
        try { state = JSON.parse(fs.readFileSync(stateFile, 'utf-8')); } catch {}
      }
      results.push({
        runId: `legacy:${legacyId}`,
        channel,
        status: state.status || 'unknown',
        uploadedUrl: state.uploadedUrl || null,
        uploadTitle: state.stepData?.upload?.title || state.uploadTitle || null,
        startedAt: state.startedAt || null,
        completedAt: state.completedAt || null,
        steps: state.steps || {},
        hasImage:
          fs.existsSync(path.join(runDir, 'background.jpg')) ||
          fs.existsSync(path.join(runDir, 'background.png')),
        source: 'legacy',
      });
    }
  }

  // ── D: 드라이브 구 대시보드 프로젝트 (접근 가능한 경우만) ─────────────
  const dDir = getDProjectsDir(channel);
  if (fs.existsSync(dDir)) {
    const dDirs = fs.readdirSync(dDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name);

    for (const projId of dDirs) {
      const runDir = path.join(dDir, projId);
      const stateFile = path.join(runDir, 'state.json');
      let state: any = { date: projId, steps: {} };
      if (fs.existsSync(stateFile)) {
        try { state = JSON.parse(fs.readFileSync(stateFile, 'utf-8')); } catch {}
      }
      const hasImage =
        fs.existsSync(path.join(runDir, 'background.jpg')) ||
        fs.existsSync(path.join(runDir, 'background.png')) ||
        fs.existsSync(path.join(runDir, 'image', 'background.jpg'));
      results.push({
        runId: `dprojects:${projId}`,
        channel,
        status: state.status || 'unknown',
        uploadedUrl: state.uploadedUrl || null,
        uploadTitle: state.stepData?.upload?.title || state.uploadTitle || null,
        startedAt: state.startedAt || null,
        completedAt: state.completedAt || null,
        steps: state.steps || {},
        hasImage,
        source: 'dprojects',
      });
    }
  }

  return results
    .sort((a, b) => (b.startedAt || '').localeCompare(a.startedAt || ''))
    .slice(0, 20);
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const channel = searchParams.get('channel') || 'DGM';
    const runId = searchParams.get('runId');

    if (runId) {
      const runDir = getRunDir(channel, runId);
      if (!runDir) return NextResponse.json({ error: '경로 오류' }, { status: 400, headers: corsHeaders });

      const stateFile = path.join(runDir, 'state.json');
      if (!fs.existsSync(stateFile)) {
        return NextResponse.json({ error: '실행 기록 없음' }, { status: 404, headers: corsHeaders });
      }
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf-8'));

      const logFile = path.join(runDir, 'meeting_log.md');
      const meetingLog = fs.existsSync(logFile)
        ? fs.readFileSync(logFile, 'utf-8').slice(0, 4000)
        : null;

      return NextResponse.json({ state, meetingLog }, { headers: corsHeaders });
    }

    const runs = listRuns(channel);
    return NextResponse.json({ runs }, { headers: corsHeaders });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
