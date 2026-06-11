import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';

export const dynamic = 'force-dynamic';

const EVOLINK_API = 'https://api.evolink.ai';
const EVOLINK_KEY = process.env.EVOLINK_KEY || '';

// ── POST: Kling Image-to-Video 생성 요청 ──────────────────────────
export async function POST(req: NextRequest) {
  try {
    const {
      imageUrl,
      imageEndUrl = '',
      prompt      = '',
      duration    = 5,
      quality     = '720p',
    } = await req.json();

    if (!imageUrl) {
      return new NextResponse(JSON.stringify({ error: 'imageUrl이 필요합니다.' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!EVOLINK_KEY) {
      return new NextResponse(JSON.stringify({ error: 'EVOLINK_KEY가 설정되지 않았습니다.' }), {
        status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const payload: Record<string, unknown> = {
      model:       'kling-v3-image-to-video',
      image_start: imageUrl,
      prompt:      prompt || 'subtle cinematic motion, gentle camera movement',
      duration:    Number(duration),
      quality,
    };

    if (imageEndUrl && imageEndUrl !== imageUrl) {
      payload.image_end = imageEndUrl;
    }

    console.log('[Kling i2v] 요청:', JSON.stringify(payload).slice(0, 300));

    const res = await fetch(`${EVOLINK_API}/v1/videos/generations`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${EVOLINK_KEY}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    console.log('[Kling i2v] 생성 응답:', JSON.stringify(data).slice(0, 500));

    if (!res.ok || data.error) {
      const msg = data.error
        ? (typeof data.error === 'object' ? JSON.stringify(data.error) : String(data.error))
        : `HTTP ${res.status}`;
      return new NextResponse(JSON.stringify({ error: msg }), {
        status: res.ok ? 500 : res.status,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    // task_id 추출 — EvoLink/Kling 두 형식 모두 대응
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

    // ── 응답 로그 (처음 600자)
    console.log('[Kling poll RAW]', taskId.slice(0, 8), JSON.stringify(raw).slice(0, 600));

    // ── 응답 구조 정규화
    // EvoLink 래퍼:  { task_id, status, data: {...} }  또는  flat
    // Kling 공식:    { code, data: { task_id, task_status, task_result: { videos:[{url}] } } }
    const inner = raw.data || raw;

    // ── status 추출 (알려진 필드명 전부 시도)
    const statusRaw: string =
      inner.task_status || inner.status || raw.status || raw.message || 'pending';

    // ── progress 추출
    const progress: number =
      inner.task_progress ?? inner.progress ?? raw.progress ?? 0;

    // ── 영상 URL 추출 — 모든 알려진 위치 시도
    //   1. Kling 공식: data.task_result.videos[0].url
    //   2. EvoLink generic: data.results[0].url  /  results[0].url  /  results[0] (URI string)
    //   3. EvoLink output:  data.output.videos[0].url
    //   4. 최상위 flat:     video_url
    const videos: any[] =
      inner.task_result?.videos ||
      inner.output?.videos ||
      inner.results ||
      raw.results || [];

    // EvoLink는 results를 URI 문자열 배열로 반환하는 경우가 있음 → 직접 꺼내기
    const videoUrl: string | null =
      videos[0]?.url || videos[0]?.video_url ||
      (typeof videos[0] === 'string' ? videos[0] : null) ||
      inner.video_url || raw.video_url || null;

    // ── 완료/오류 판정
    const DONE_STATUSES  = ['completed','succeed','success','succeeded','done','SUCCEED','COMPLETED','SUCCESS'];
    const ERROR_STATUSES = ['failed','error','fail','FAILED','ERROR'];

    const isDone  = DONE_STATUSES.includes(statusRaw) || (progress >= 100 && !!videoUrl);
    const isError = ERROR_STATUSES.includes(statusRaw);

    // isDone인데 videoUrl이 없으면 rawLog를 보고 오류 처리
    if (isDone && !videoUrl) {
      console.warn('[Kling poll] 완료됐지만 videoUrl 추출 실패. raw:', JSON.stringify(raw).slice(0, 600));
    }

    return new NextResponse(JSON.stringify({
      status:   isDone ? 'done' : isError ? 'error' : 'processing',
      progress: isDone ? 100 : progress,
      videoUrl: isDone ? videoUrl : null,
      rawStatus: statusRaw,   // 디버깅용
      rawLog:    JSON.stringify(raw).slice(0, 300),  // 디버깅용
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
