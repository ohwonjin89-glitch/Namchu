import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';
import * as path from 'path';
import { getChannelsBase } from '@/lib/serverPaths';

export const dynamic = 'force-dynamic';

const CHANNELS_BASE = getChannelsBase();

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file     = formData.get('file')    as File   | null;
    const channel  = formData.get('channel') as string | null;

    if (!file || !channel) {
      return new NextResponse(JSON.stringify({ error: 'file과 channel이 필요합니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const ext     = path.extname(file.name).toLowerCase();
    const allowed = ['.mp4', '.mov', '.webm', '.avi'];
    if (!allowed.includes(ext)) {
      return new NextResponse(JSON.stringify({ error: '허용되지 않는 파일 형식입니다. (mp4/mov/webm/avi)' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const safeName    = file.name.replace(/[\\/:*?"<>|]/g, '_');
    const channelDir  = path.join(CHANNELS_BASE, channel);
    const savePath    = path.join(channelDir, safeName);

    fs.mkdirSync(channelDir, { recursive: true });

    const arrayBuffer = await file.arrayBuffer();
    fs.writeFileSync(savePath, Buffer.from(arrayBuffer));

    return new NextResponse(JSON.stringify({ savedPath: savePath, fileName: safeName }), {
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
