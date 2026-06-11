import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';

export const dynamic = 'force-dynamic';

const ALLOWED_BASE = 'D:\\AI Agent\\Claude\\channels';

export async function DELETE(req: NextRequest) {
  try {
    const { filePath } = await req.json();

    if (!filePath) {
      return new NextResponse(JSON.stringify({ error: 'filePath가 필요합니다.' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    // 허용된 경로 외 삭제 방지
    if (!filePath.startsWith(ALLOWED_BASE)) {
      return new NextResponse(JSON.stringify({ error: '허용되지 않는 경로입니다.' }), {
        status: 403, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    if (!fs.existsSync(filePath)) {
      return new NextResponse(JSON.stringify({ error: '파일을 찾을 수 없습니다.' }), {
        status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    fs.unlinkSync(filePath);

    return new NextResponse(JSON.stringify({ ok: true }), {
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
