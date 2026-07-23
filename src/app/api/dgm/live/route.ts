import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const LIVE_STATE_PATH = path.join(
  process.env.LOCALAPPDATA || 'C:\\Users\\오원진\\AppData\\Local',
  'dgm_output', 'DGM_Playlist', 'live_state.json'
);

// GET — 현재 라이브 상태 반환
export async function GET(_req: NextRequest) {
  try {
    if (!fs.existsSync(LIVE_STATE_PATH)) {
      return NextResponse.json({ exists: false }, { headers: corsHeaders });
    }
    const state = JSON.parse(fs.readFileSync(LIVE_STATE_PATH, 'utf-8'));
    return NextResponse.json({ exists: true, state }, { headers: corsHeaders });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}

// DELETE — 세션 초기화 (새 테스트 시작 전)
export async function DELETE(_req: NextRequest) {
  try {
    if (fs.existsSync(LIVE_STATE_PATH)) {
      fs.unlinkSync(LIVE_STATE_PATH);
    }
    return NextResponse.json({ ok: true }, { headers: corsHeaders });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}
