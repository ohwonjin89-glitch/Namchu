import { NextResponse, NextRequest } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { corsHeaders } from "@/lib/utils";

export const maxDuration = 60;
export const dynamic = "force-dynamic";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  try {
    const { videos = [], keywords = [], channel = "Playlisttann" } = await req.json();

    const videoList = videos
      .slice(0, 10)
      .map(
        (v: any, i: number) =>
          `${i + 1}. "${v.title}" — ${(v.viewCount / 10000).toFixed(0)}만 조회 (${v.channelTitle})`
      )
      .join("\n");

    const kwList = keywords
      .slice(0, 15)
      .map((k: any) => k.word)
      .join(", ");

    const GENRES = [
      "Lo-fi Focus & Cafe Chill",
      "Groove Hip-hop & Chill Pop",
      "Late Night R&B & Soul",
      "Upbeat City Pop & Funk Groove",
      "Acoustic Indie Pop & Folk Soul",
      "Chillwave & Synth Pop",
      "Jazz-hop & Bossa Nova Chill",
    ];

    const systemPrompt = `You are a YouTube music playlist channel analyst for Korean channels.
Analyze trending video data and provide concise, actionable insights in Korean.
You must also recommend one genre from the provided list that best fits the trend.`;

    const userPrompt = `다음은 이번 주 국내 플레이리스트 YouTube 인기 영상 TOP 10입니다:

${videoList || "데이터 없음"}

핵심 키워드: ${kwList || "없음"}

이 데이터를 분석해서 아래 3가지를 한국어로 간결하게 알려주세요:

1. 🏷️ **주요 주제/분위기**: 가장 조회수가 높은 분위기 또는 상황 (카페, 새벽, 드라이브 등 구체적으로)
2. 🔍 **공통 패턴**: 제목 형식, 이모지 사용, 분위기 키워드 등 눈에 띄는 공통점
3. 💡 **다음 업로드 추천**: 이 트렌드를 바탕으로 "${channel}" 채널이 제작하면 좋을 영상 주제 1가지 (구체적 제목 예시 포함)

각 항목을 1-2문장으로 작성해주세요. 이모지를 활용해 가독성을 높여주세요.

---
마지막으로, 트렌드를 가장 잘 반영하는 장르를 아래 목록에서 정확히 1개 선택해 JSON으로 응답해주세요:
${GENRES.map((g, i) => `${i + 1}. ${g}`).join("\n")}

응답 형식 (insight 텍스트 다음 줄에):
RECOMMENDED_GENRE_JSON:{"genre":"여기에 장르명"}`;

    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 800,
      messages: [{ role: "user", content: userPrompt }],
      system: systemPrompt,
    });

    const raw = (message.content[0] as { type: string; text: string }).text.trim();

    // 장르 JSON 파싱 시도
    let insight = raw;
    let recommendedGenre = "";
    const genreMatch = raw.match(/RECOMMENDED_GENRE_JSON:\{"genre":"([^"]+)"\}/);
    if (genreMatch) {
      recommendedGenre = genreMatch[1];
      insight = raw.replace(/\n*RECOMMENDED_GENRE_JSON:\{"genre":"[^"]+"\}/, "").trim();
    }

    // 장르 유효성 검증
    if (!GENRES.includes(recommendedGenre)) recommendedGenre = "";

    return new NextResponse(JSON.stringify({ insight, recommendedGenre }), {
      status: 200,
      headers: { "Content-Type": "application/json", ...corsHeaders },
    });
  } catch (error: any) {
    console.error("trend-insight error:", error);
    return new NextResponse(
      JSON.stringify({ error: error.message || String(error) }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}
