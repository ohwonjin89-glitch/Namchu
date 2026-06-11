import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';

export const dynamic = 'force-dynamic';

const EVOLINK_API = 'https://api.evolink.ai';
const EVOLINK_KEY = process.env.EVOLINK_KEY || '';

// ── POST: Nano Banana 2 이미지 생성 요청 ──────────────────────────
export async function POST(req: NextRequest) {
  try {
    const {
      prompt    = '',
      imageUrls = [],
      size      = '16:9',
      quality   = '2K',
    } = await req.json();

    if (!prompt && imageUrls.length === 0) {
      return new NextResponse(JSON.stringify({ error: '프롬프트 또는 이미지가 필요합니다.' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!EVOLINK_KEY) {
      return new NextResponse(JSON.stringify({ error: 'EVOLINK_KEY가 설정되지 않았습니다.' }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const payload: Record<string, unknown> = {
      model:   'gemini-3.1-flash-image-preview',
      prompt,
      size,
      quality,
    };

    if (Array.isArray(imageUrls) && imageUrls.length > 0) {
      payload.image_urls = imageUrls;
    }

    console.log('[NB2] 요청:', JSON.stringify(payload).slice(0, 400));

    const res = await fetch(`${EVOLINK_API}/v1/images/generations`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${EVOLINK_KEY}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    console.log('[NB2] 생성 응답:', JSON.stringify(data).slice(0, 500));

    if (!res.ok || data.error) {
      const msg = data.error
        ? (typeof data.error === 'object' ? JSON.stringify(data.error) : String(data.error))
        : `HTTP ${res.status}`;
      return new NextResponse(JSON.stringify({ error: msg }), {
        status: res.ok ? 500 : res.status,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const taskId =
      data.task_id || data.id ||
      data.data?.task_id || data.data?.id || null;

    if (!taskId) {
      return new NextResponse(JSON.stringify({ error: 'task_id를 받지 못했습니다.', raw: data }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    return new NextResponse(JSON.stringify({ taskId }), {
      status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });

  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

// ── GET: 생성 상태 폴링 ────────────────────────────────────────────
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const taskId = searchParams.get('taskId');

  if (!taskId) {
    return new NextResponse(JSON.stringify({ error: 'taskId가 필요합니다.' }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }

  try {
    const res = await fetch(`${EVOLINK_API}/v1/tasks/${taskId}`, {
      headers: { 'Authorization': `Bearer ${EVOLINK_KEY}` },
    });
    const raw = await res.json();

    console.log('[NB2 poll]', taskId.slice(0, 8), JSON.stringify(raw).slice(0, 600));

    const inner = raw.data || raw;

    const statusRaw: string =
      inner.task_status || inner.status || raw.status || 'pending';

    const progress: number =
      inner.task_progress ?? inner.progress ?? raw.progress ?? 0;

    // 이미지 URL 추출 — results가 URI 문자열 배열이거나 객체 배열일 수 있음
    const results: any[] =
      inner.task_result?.images ||
      inner.output?.images ||
      inner.results ||
      raw.results || [];

    const imageUrl: string | null =
      results[0]?.url || results[0]?.image_url ||
      (typeof results[0] === 'string' ? results[0] : null) ||
      inner.image_url || raw.image_url || null;

    const DONE_STATUSES  = ['completed','succeed','success','succeeded','done','SUCCEED','COMPLETED','SUCCESS'];
    const ERROR_STATUSES = ['failed','error','fail','FAILED','ERROR'];

    const isDone  = DONE_STATUSES.includes(statusRaw) || (progress >= 100 && !!imageUrl);
    const isError = ERROR_STATUSES.includes(statusRaw);

    if (isDone && !imageUrl) {
      console.warn('[NB2 poll] 완료됐지만 imageUrl 추출 실패. raw:', JSON.stringify(raw).slice(0, 600));
    }

    return new NextResponse(JSON.stringify({
      status:   isDone ? 'done' : isError ? 'error' : 'processing',
      progress: isDone ? 100 : progress,
      imageUrl: isDone ? imageUrl : null,
      rawStatus: statusRaw,
      rawLog:    JSON.stringify(raw).slice(0, 300),
    }), {
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
