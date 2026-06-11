import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';

export const dynamic = 'force-dynamic';

const EVOLINK_FILES_API = 'https://files-api.evolink.ai';
const EVOLINK_KEY       = process.env.EVOLINK_KEY || '';

// 로컬 이미지(base64)를 EvoLink CDN에 업로드해서 공개 URL 반환
// 대시보드에서 blob URL 이미지를 Kling에 넘길 때 사용
export async function POST(req: NextRequest) {
  try {
    const { base64 } = await req.json();
    if (!base64) {
      return new NextResponse(JSON.stringify({ error: 'base64 데이터가 필요합니다.' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const base64Only = base64.startsWith('data:') ? base64.split(',')[1] : base64;

    const res = await fetch(`${EVOLINK_FILES_API}/api/v1/files/upload/base64`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${EVOLINK_KEY}`,
      },
      body: JSON.stringify({ base64_data: base64Only }),
    });

    const data = await res.json();
    const url = data.url || data.file_url || data.download_url
      || data.data?.url || data.data?.file_url || null;

    if (!url) {
      return new NextResponse(JSON.stringify({ error: 'URL을 받지 못했습니다.', raw: data }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    return new NextResponse(JSON.stringify({ url }), {
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
