import { NextResponse, NextRequest } from "next/server";
import { corsHeaders } from "@/lib/utils";

export const dynamic = "force-dynamic";

const EVOLINK_API      = 'https://api.evolink.ai';
const EVOLINK_FILES_API = 'https://files-api.evolink.ai';
const EVOLINK_KEY      = process.env.EVOLINK_KEY || '';

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// base64 데이터URL → evolink.ai 파일 서버에 업로드 → 공개 URL 반환
async function uploadBase64(dataUrl: string): Promise<string | null> {
  try {
    // data:image/jpeg;base64,... 형태인 경우 순수 base64만 추출
    const base64Only = dataUrl.startsWith('data:') ? dataUrl.split(',')[1] : dataUrl;

    // evolink Files API는 "Base64Data" 필드명을 요구함 (로그에서 확인)
    const res = await fetch(`${EVOLINK_FILES_API}/api/v1/files/upload/base64`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${EVOLINK_KEY}`,
      },
      body: JSON.stringify({ base64_data: base64Only }),
    });
    const data = await res.json();
    console.log('[MJ] 파일업로드 응답:', JSON.stringify(data));
    return data.url || data.file_url || data.download_url
      || data.data?.url || data.data?.file_url || data.data?.download_url || null;
  } catch (e) {
    console.warn('[MJ] 파일업로드 실패:', e);
    return null;
  }
}

// base64 배열을 병렬 업로드하고 성공한 URL 배열만 반환
async function uploadAllBase64(base64List: string[]): Promise<string[]> {
  const results = await Promise.all(base64List.map(uploadBase64));
  return results.filter((u): u is string => !!u);
}

// --param 이 이미 프롬프트에 있는지 확인
const hasParam = (p: string, param: string) =>
  new RegExp(`--${param}(\\s|$)`).test(p);

// --q 값을 MJ V7 허용 범위로 보정 (0.25 / 0.5 / 1)
function sanitizeQuality(prompt: string): string {
  return prompt.replace(/--q\s+(\S+)/g, (_m, val) => {
    const n = parseFloat(val);
    if (isNaN(n) || n >= 1) return '--q 1';
    if (n >= 0.5) return '--q 0.5';
    return '--q 0.25';
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      mode      = 'generate',
      prompt    = '',
      noPrompt  = '',
      imageUrl  = '',           // variation/remix/upscale 등에서 소스 이미지 URL
      imgUrls   = [] as string[],
      imgBase64 = [] as string[],
      srefUrls  = [] as string[],
      srefBase64 = [] as string[],
      orefUrl   = '',
      orefBase64 = '',
      speed     = 'fast',
      stylize   = 100,
      chaos     = 0,
      weird     = 0,
      quality   = 1,
      iwValue   = 2.5,
      ar        = '16:9',
      raw       = false,
    } = body;

    if (!EVOLINK_KEY) {
      return new NextResponse(JSON.stringify({ error: 'EVOLINK_KEY가 .env에 설정되지 않았습니다.' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    // ── 1. 업로드된 파일(base64) → evolink.ai 공개 URL로 변환 ──────────────
    console.log('[MJ] 파일 업로드 시작... srefBase64:', srefBase64.length, '개 | imgBase64:', imgBase64.length, '개 | orefBase64:', !!orefBase64);

    const [uploadedSrefUrls, uploadedImgUrls, uploadedOrefUrl] = await Promise.all([
      srefBase64.length  ? uploadAllBase64(srefBase64)                        : Promise.resolve([] as string[]),
      imgBase64.length   ? uploadAllBase64(imgBase64)                         : Promise.resolve([] as string[]),
      orefBase64 && !orefUrl ? uploadBase64(orefBase64)                       : Promise.resolve(null),
    ]);

    const allSrefUrls = [...srefUrls,  ...uploadedSrefUrls];
    const allImgUrls  = [...imgUrls,   ...uploadedImgUrls];
    const finalOrefUrl = orefUrl || uploadedOrefUrl || '';

    // ── 2. 프롬프트 조립 ────────────────────────────────────────────────────
    // 이미지 프롬프트 URL은 MJ 관례상 프롬프트 맨 앞에 위치
    let fullPrompt = allImgUrls.length
      ? allImgUrls.join(' ') + ' ' + prompt.trim()
      : prompt.trim();

    // --iw (이미지 가중치): IMAGE PROMPT 이미지가 있을 때 슬라이더 값으로 추가
    if (allImgUrls.length > 0 && !hasParam(fullPrompt, 'iw')) {
      fullPrompt += ` --iw ${iwValue}`;
    }

    // --sref (스타일 참조): 업로드된 이미지 + 수동 입력 URL
    if (allSrefUrls.length > 0 && !hasParam(fullPrompt, 'sref')) {
      fullPrompt += ` --sref ${allSrefUrls.join(' ')}`;
    }

    // --oref (오브젝트 참조)
    if (finalOrefUrl && !hasParam(fullPrompt, 'oref')) {
      fullPrompt += ` --oref ${finalOrefUrl}`;
    }

    // --no (네거티브)
    if (noPrompt && !hasParam(fullPrompt, 'no')) {
      fullPrompt += ` --no ${noPrompt}`;
    }

    // --ar (비율) - 없을 때만 추가
    if (!hasParam(fullPrompt, 'ar')) fullPrompt += ` --ar ${ar}`;

    // --s (스타일라이즈) - 가이드에서 파싱한 값 or 100 기본값
    if (stylize !== 100 && !hasParam(fullPrompt, 's') && !hasParam(fullPrompt, 'stylize')) {
      fullPrompt += ` --s ${stylize}`;
    }

    // --c (카오스)
    if (chaos > 0 && !hasParam(fullPrompt, 'c') && !hasParam(fullPrompt, 'chaos')) {
      fullPrompt += ` --c ${chaos}`;
    }

    // --w (위어드)
    if (weird > 0 && !hasParam(fullPrompt, 'w') && !hasParam(fullPrompt, 'weird')) {
      fullPrompt += ` --w ${weird}`;
    }

    // --q (품질) - 대시보드 QUALITY 셀렉터 값 반영
    if (!hasParam(fullPrompt, 'q')) {
      const validQ = quality >= 1 ? 1 : quality >= 0.5 ? 0.5 : 0.25;
      if (validQ < 1) fullPrompt += ` --q ${validQ}`;
    }

    // --raw
    if (raw && !hasParam(fullPrompt, 'raw')) fullPrompt += ` --raw`;

    // --q 값 자동 보정 (가이드에 잘못된 값 있을 경우 대비)
    fullPrompt = sanitizeQuality(fullPrompt);

    // --sw (style weight): --sref 없이 단독 사용 시 오류 → 제거
    if (!hasParam(fullPrompt, 'sref')) {
      fullPrompt = fullPrompt.replace(/--sw\s+\S+/g, '').replace(/\s{2,}/g, ' ').trim();
    }

    // MJ V7 미지원 파라미터 제거 (--exp, --stop 등 비표준 플래그)
    fullPrompt = fullPrompt
      .replace(/--exp\s+\S*/g, '')
      .replace(/--stop\s+\d+/g, '')
      .replace(/\s{2,}/g, ' ')
      .trim();

    console.log('[MJ] 최종 프롬프트:', fullPrompt);
    console.log('[MJ] speed:', speed, '| quality:', quality, '| mode:', mode);
    console.log('[MJ] sref URLs:', allSrefUrls.length, '개 →', allSrefUrls.join(', ') || '없음');
    console.log('[MJ] img URLs:', allImgUrls.length, '개 | oref:', finalOrefUrl || '없음');

    // ── 3. evolink.ai에 이미지 생성 요청 제출 ───────────────────────────────
    const requestBody: Record<string, any> = {
      model: 'mj-v7',
      prompt: fullPrompt,
      model_params: { speed },
    };

    // variation / remix 등 소스 이미지가 필요한 모드
    if (imageUrl && mode !== 'generate') {
      requestBody.image_url = imageUrl;
    }

    const submitRes = await fetch(`${EVOLINK_API}/v1/images/generations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${EVOLINK_KEY}`,
      },
      body: JSON.stringify(requestBody),
    });

    const submitData = await submitRes.json();
    console.log('[MJ] evolink 제출 응답:', JSON.stringify(submitData));

    if (!submitRes.ok || !submitData.id) {
      const errMsg = submitData.error?.message || submitData.error || `HTTP ${submitRes.status}`;
      return new NextResponse(JSON.stringify({ error: String(errMsg) }), {
        status: submitRes.status || 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const taskId = submitData.id;

    // ── 4. 완료될 때까지 폴링 (최대 5분) ────────────────────────────────────
    const maxWait = 300000;
    const start   = Date.now();

    while (Date.now() - start < maxWait) {
      await sleep(5000);

      const pollRes  = await fetch(`${EVOLINK_API}/v1/tasks/${taskId}`, {
        headers: { 'Authorization': `Bearer ${EVOLINK_KEY}` },
      });
      const pollData = await pollRes.json();

      console.log('[MJ] 폴링 상태:', pollData.status, '| progress:', pollData.progress);

      if (pollData.status === 'completed' && pollData.results?.length) {
        return new NextResponse(JSON.stringify({ images: pollData.results }), {
          status: 200,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }

      if (pollData.status === 'failed') {
        return new NextResponse(JSON.stringify({ error: String(pollData.error || '이미지 생성 실패') }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }
    }

    return new NextResponse(JSON.stringify({ error: '생성 시간 초과 (5분). 나중에 다시 시도해주세요.' }), {
      status: 504,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });

  } catch (error: any) {
    return new NextResponse(JSON.stringify({
      error: error.message || '서버 내부 오류'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
