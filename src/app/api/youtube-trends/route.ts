import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as path from 'path';
import { getPythonCommand } from '@/lib/pythonEnv';

export const dynamic = 'force-dynamic';
export const maxDuration = 120;

const SCRIPT_PATH = path.join(process.cwd(), 'scripts', 'youtube_trends.py');

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
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
