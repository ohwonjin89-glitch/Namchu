import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';
import * as path from 'path';
import { getWorkBase } from '@/lib/serverPaths';

export const dynamic = 'force-dynamic';

const TEMP_DIR = path.join(getWorkBase(), 'temp', 'background');

export async function POST(req: NextRequest) {
  try {
    const { base64, fileName } = await req.json();

    if (!base64 || !fileName) {
      return new NextResponse(JSON.stringify({ error: 'base64와 fileName이 필요합니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    fs.mkdirSync(TEMP_DIR, { recursive: true });

    // 확장자 추출 (jpg, png, jpeg, webp 만 허용)
    const ext = path.extname(fileName).toLowerCase();
    const allowed = ['.jpg', '.jpeg', '.png', '.webp'];
    const safeExt = allowed.includes(ext) ? ext : '.jpg';
    const saveName = 'uploaded_background' + safeExt;
    const localPath = path.join(TEMP_DIR, saveName);

    const buffer = Buffer.from(base64, 'base64');
    fs.writeFileSync(localPath, buffer);

    return new NextResponse(JSON.stringify({ localPath }), {
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
