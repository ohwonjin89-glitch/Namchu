import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const { renames } = await req.json();
    // renames: Array<{ dir: string, oldName: string, newName: string }>

    if (!Array.isArray(renames)) {
      return new NextResponse(JSON.stringify({ error: 'renames 배열이 필요합니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const results: Array<{ oldName: string; newName: string; ok: boolean; error?: string }> = [];

    for (const item of renames) {
      const { dir, oldName, newName } = item;
      if (!dir || !oldName || !newName) continue;
      const oldPath = path.join(dir, oldName);
      const newPath = path.join(dir, newName);
      try {
        if (fs.existsSync(oldPath)) {
          fs.renameSync(oldPath, newPath);
          results.push({ oldName, newName, ok: true });
        } else {
          results.push({ oldName, newName, ok: false, error: '파일 없음' });
        }
      } catch (e: any) {
        results.push({ oldName, newName, ok: false, error: e.message });
      }
    }

    return new NextResponse(JSON.stringify({ success: true, results }), {
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
