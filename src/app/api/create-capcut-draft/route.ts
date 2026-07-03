import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as path from 'path';
import { getPythonCommand } from '@/lib/pythonEnv';

export const dynamic = 'force-dynamic';
export const maxDuration = 120;

const SCRIPT_PATH = path.join(process.cwd(), 'scripts', 'create_capcut_draft.py');
const CAPCUT_DRAFT_FOLDER = 'C:\\Users\\오원진\\AppData\\Local\\CapCut\\User Data\\Projects\\com.lveditor.draft';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const params = {
      draftFolderPath: CAPCUT_DRAFT_FOLDER,
      draftName: body.draftName || 'AI_Studio_Draft',
      bgImagePath:  body.bgImagePath  || '',
      bgVideoPath:  body.bgVideoPath  || '',
      musicFiles:   body.musicFiles   || [],
      logoPath:     body.logoPath     || '',
      logoScale:    body.logoScale    ?? 0.38,
      logoX:        body.logoX        ?? 0.0,
      logoY:        body.logoY        ?? -0.42,
      logoAlpha:    body.logoAlpha    ?? 1.0,
      textOverlays: body.textOverlays || [],
      width:        body.width        || 1920,
      height:       body.height       || 1080,
      fps:          body.fps          || 30,
    };

    const result = await runPython(SCRIPT_PATH, JSON.stringify(params));
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
        // 마지막 JSON 라인만 파싱
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
