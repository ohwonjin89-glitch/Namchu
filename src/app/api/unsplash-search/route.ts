import { NextResponse, NextRequest } from "next/server";
import { corsHeaders } from "@/lib/utils";

export const dynamic = "force-dynamic";

// 확인된 Unsplash 사진 ID (tools.py _UNSPLASH_PHOTO_MAP 기반)
const THEME_PHOTOS: Record<string, Array<{ id: string; desc: string }>> = {
  cafe: [
    { id: "1554118811-1e0d58224f24", desc: "카페 · 여성 · 웜톤" },
    { id: "1495474472287-4d71bcdd2085", desc: "창가 · 아침 · 커피" },
    { id: "1481349518771-20055b2a7b24", desc: "독서 · 카페 · 빈티지" },
    { id: "1509042239860-f550ce710b93", desc: "코지 · 실내 · 빛" },
    { id: "1521017432531-fbd92d768814", desc: "무디 · 포트레이트" },
    { id: "1442512595331-e89e73853f31", desc: "혼자 · 감성 · 카페" },
    { id: "1508739773434-c26b3d09e071", desc: "필름 · 카페 · 감성" },
    { id: "1544005313-94ddf0286df2", desc: "웜톤 · 인물" },
    { id: "1501339847302-ac426a4a7cbb", desc: "커피 · 아침 빛" },
    { id: "1559305616-3f99cd43e353", desc: "한국 감성 · 카페" },
  ],
  night: [
    { id: "1467269204519-bf7b702a32b2", desc: "새벽 · 도시 · 야경" },
    { id: "1519120944692-1a8d8cfc107f", desc: "밤 · 감성 · 빛" },
    { id: "1444703686981-a3abbc4d4fe3", desc: "밤하늘 · 별빛" },
    { id: "1519681393784-d120267933ba", desc: "산 · 별 · 새벽" },
    { id: "1531219572328-a0171b4448a3", desc: "새벽 · 혼자 · 조용함" },
    { id: "1508214751196-bcfd4ca60f91", desc: "새벽 · 빛 · 감성" },
    { id: "1477959858617-67f85cf4f1df", desc: "도시 · 야경 · 감성" },
    { id: "1444084686090-f06a8a29e43e", desc: "야간 · 빌딩 · 현대" },
    { id: "1486325212027-8081e485255e", desc: "도시 · 네온 · 밤" },
    { id: "1555952517-2e8e729e0960", desc: "도시 · 거리 · 밤" },
  ],
  drive: [
    { id: "1449824913935-59a10b8d2000", desc: "드라이브 · 도로 · 밤" },
    { id: "1545558014-8692077e9b5c", desc: "드라이브 · 노을" },
    { id: "1485163819542-3d5b2fa11b40", desc: "하이웨이 · 자유" },
    { id: "1506905925346-21bda4d32df4", desc: "도로 · 감성" },
    { id: "1467269204519-bf7b702a32b2", desc: "야간 드라이브" },
    { id: "1477959858617-67f85cf4f1df", desc: "도시 · 드라이브" },
    { id: "1444084686090-f06a8a29e43e", desc: "빌딩 · 드라이브" },
    { id: "1519120944692-1a8d8cfc107f", desc: "밤 드라이브 · 빛" },
    { id: "1486325212027-8081e485255e", desc: "네온 · 드라이브" },
    { id: "1555952517-2e8e729e0960", desc: "거리 · 드라이브" },
  ],
  summer: [
    { id: "1507525428034-b723cf961d3e", desc: "여름 · 해변 · 하늘" },
    { id: "1476231682828-37e571bc172f", desc: "여름 · 바다 · 설렘" },
    { id: "1502680390469-be75c86b636f", desc: "여름 · 물 · 여유" },
    { id: "1505118380757-91f5f5632de0", desc: "여름 · 풀장 · 감성" },
    { id: "1469854523086-cc02fe5d8800", desc: "여름 · 여행" },
    { id: "1488646953014-85cb44e25828", desc: "여름 · 해외여행" },
    { id: "1476514525535-07fb3b4ae5f1", desc: "여름 · 경치" },
    { id: "1501854140801-50d01698950b", desc: "여름 · 자연" },
    { id: "1441974231531-c6227db76b6e", desc: "여름 · 초록" },
    { id: "1418065460487-3e41a6c84dc5", desc: "여름 · 자연광" },
  ],
  rainy: [
    { id: "1515705576963-95cad62945b6", desc: "비 · 창가 · 감성" },
    { id: "1509315307596-f9b10a9ddaf6", desc: "비 오는 날 · 창문" },
    { id: "1519682577862-22b62b24cb73", desc: "빗소리 · 혼자" },
    { id: "1534274988757-a79023d7f947", desc: "비 · 우산 · 감성" },
    { id: "1509042239860-f550ce710b93", desc: "비 오는 날 · 실내" },
    { id: "1481349518771-20055b2a7b24", desc: "비 · 카페 · 혼자" },
    { id: "1467269204519-bf7b702a32b2", desc: "비 오는 밤" },
    { id: "1519120944692-1a8d8cfc107f", desc: "비 · 야경" },
    { id: "1521017432531-fbd92d768814", desc: "비 · 무드" },
    { id: "1544005313-94ddf0286df2", desc: "빗소리 · 감성" },
  ],
  nature: [
    { id: "1441974231531-c6227db76b6e", desc: "숲 · 자연 · 힐링" },
    { id: "1418065460487-3e41a6c84dc5", desc: "자연광 · 초록" },
    { id: "1501854140801-50d01698950b", desc: "자연 · 여유" },
    { id: "1448375240586-882707db888b", desc: "자연 · 풀밭" },
    { id: "1476514525535-07fb3b4ae5f1", desc: "경치 · 자연" },
    { id: "1469854523086-cc02fe5d8800", desc: "산 · 여행 · 자연" },
    { id: "1519681393784-d120267933ba", desc: "밤 산 · 별" },
    { id: "1507525428034-b723cf961d3e", desc: "바다 · 자연" },
    { id: "1502680390469-be75c86b636f", desc: "물 · 자연" },
    { id: "1488646953014-85cb44e25828", desc: "자연 · 여행" },
  ],
  study: [
    { id: "1456735190827-d1262f71b8a3", desc: "공부 · 책상 · 집중" },
    { id: "1507842217343-583bb7270b66", desc: "도서관 · 책 · 집중" },
    { id: "1513475382585-d06e58bcb0e0", desc: "스터디 · 카페" },
    { id: "1497633762265-9d179a990aa6", desc: "책 · 독서 · 집중" },
    { id: "1481349518771-20055b2a7b24", desc: "독서 · 빈티지 · 카페" },
    { id: "1509042239860-f550ce710b93", desc: "집중 · 실내 · 빛" },
    { id: "1554118811-1e0d58224f24", desc: "카페 · 스터디 · 집중" },
    { id: "1495474472287-4d71bcdd2085", desc: "커피 · 공부 · 아침" },
    { id: "1501339847302-ac426a4a7cbb", desc: "아침 · 커피 · 시작" },
    { id: "1559305616-3f99cd43e353", desc: "카페 · 집중 · 감성" },
  ],
  urban: [
    { id: "1477959858617-67f85cf4f1df", desc: "도시 · 야경 · 감성" },
    { id: "1444084686090-f06a8a29e43e", desc: "도시 · 빌딩 · 현대" },
    { id: "1486325212027-8081e485255e", desc: "도시 · 네온 · 밤" },
    { id: "1555952517-2e8e729e0960", desc: "도시 · 거리 · 감성" },
    { id: "1467269204519-bf7b702a32b2", desc: "도심 · 야경" },
    { id: "1519120944692-1a8d8cfc107f", desc: "도시 · 빛 · 밤" },
    { id: "1449824913935-59a10b8d2000", desc: "도시 · 도로 · 밤" },
    { id: "1545558014-8692077e9b5c", desc: "도시 · 노을" },
    { id: "1485163819542-3d5b2fa11b40", desc: "도시 · 자유" },
    { id: "1506905925346-21bda4d32df4", desc: "도시 · 길" },
  ],
  travel: [
    { id: "1469854523086-cc02fe5d8800", desc: "여행 · 항공 · 설렘" },
    { id: "1488646953014-85cb44e25828", desc: "여행 · 해외 · 감성" },
    { id: "1476514525535-07fb3b4ae5f1", desc: "여행 · 경치 · 풍경" },
    { id: "1452421822248-d4c2b47f0c81", desc: "여행 · 자유 · 감성" },
    { id: "1507525428034-b723cf961d3e", desc: "여행 · 바다" },
    { id: "1476231682828-37e571bc172f", desc: "여행 · 해변" },
    { id: "1441974231531-c6227db76b6e", desc: "여행 · 자연" },
    { id: "1501854140801-50d01698950b", desc: "여행 · 자연광" },
    { id: "1448375240586-882707db888b", desc: "여행 · 들판" },
    { id: "1418065460487-3e41a6c84dc5", desc: "여행 · 풍경" },
  ],
};

function detectTheme(kw: string): string {
  const lkw = kw.toLowerCase();
  const patterns: Array<[RegExp, string]> = [
    [/cafe|카페|coffee|커피|cozy|latte|espresso/, "cafe"],
    [/night|새벽|midnight|late night|dark|심야|dim/, "night"],
    [/drive|드라이브|highway|road|자동차|car window/, "drive"],
    [/rain|비|rainy|window rain|storm|빗소리/, "rainy"],
    [/summer|여름|beach|바다|ocean|sea|해변|해수욕/, "summer"],
    [/study|공부|focus|책|book|library|desk|집중/, "study"],
    [/city|urban|도시|neon|downtown|도심/, "urban"],
    [/nature|자연|forest|mountain|green|landscape|숲|힐링|healing/, "nature"],
    [/travel|여행|wander|vacation|trip|scenic/, "travel"],
  ];
  for (const [pattern, theme] of patterns) {
    if (pattern.test(lkw)) return theme;
  }
  return "cafe";
}

const THEME_TO_ENGLISH: Record<string, string> = {
  cafe: "cafe coffee aesthetic warm woman",
  night: "midnight dark aesthetic moody city",
  drive: "night drive highway scenic road",
  rainy: "rainy day window cozy indoor",
  summer: "summer beach ocean aesthetic warm",
  study: "study desk book aesthetic library",
  urban: "city urban neon night aesthetic",
  nature: "nature forest green peaceful landscape",
  travel: "travel scenic landscape aesthetic adventure",
};

function makeFallbackPhotos(theme: string) {
  const ids = THEME_PHOTOS[theme] || THEME_PHOTOS.cafe;
  return ids.map((p) => ({
    thumb: `https://images.unsplash.com/photo-${p.id}?w=400&h=225&fit=crop&auto=format`,
    full: `https://images.unsplash.com/photo-${p.id}?w=1920&h=1080&fit=crop&auto=format`,
    desc: p.desc,
  }));
}

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.get("q") || "";
  const theme = detectTheme(query);
  const key = process.env.UNSPLASH_ACCESS_KEY || "";

  if (!key) {
    return new NextResponse(
      JSON.stringify({ photos: makeFallbackPhotos(theme), theme, fallback: true }),
      { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }

  try {
    // 한국어 키워드는 테마 기반 영어 검색어로 변환
    const searchQuery = /[가-힣]/.test(query)
      ? THEME_TO_ENGLISH[theme] || "aesthetic music playlist mood"
      : query;

    const url = `https://api.unsplash.com/search/photos?query=${encodeURIComponent(searchQuery)}&per_page=10&orientation=landscape&client_id=${key}`;
    const res = await fetch(url, { headers: { "Accept-Version": "v1" } });

    if (!res.ok) throw new Error(`Unsplash API ${res.status}`);

    const data = await res.json();
    const photos = (data.results || [])
      .map((p: any) => ({
        thumb: p.urls?.small || p.urls?.regular || "",
        full: p.urls?.regular || p.urls?.full || "",
        desc: (p.alt_description || p.description || searchQuery)
          .slice(0, 30),
        author: p.user?.name,
      }))
      .filter((p: any) => p.thumb && p.full);

    if (!photos.length) throw new Error("No results");

    return new NextResponse(
      JSON.stringify({ photos, theme, fallback: false }),
      { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  } catch {
    return new NextResponse(
      JSON.stringify({ photos: makeFallbackPhotos(theme), theme, fallback: true }),
      { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}
