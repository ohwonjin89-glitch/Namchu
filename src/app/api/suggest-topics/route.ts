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
      .map((v: any, i: number) => `${i + 1}. "${v.title}" — ${(v.viewCount / 10000).toFixed(0)}만 조회 (${v.channelTitle})`)
      .join("\n");

    const kwList = keywords
      .slice(0, 15)
      .map((k: any) => k.word)
      .join(", ");

    const systemPrompt = `You are a YouTube playlist channel strategist specializing in Korean music channels.
Analyze trend data and suggest 4 video topics. Return ONLY a valid JSON array, no markdown, no explanation.`;

    const userPrompt = `Channel: ${channel}

Top trending playlist videos this week:
${videoList || "데이터 없음"}

Core keywords from trending videos:
${kwList || "없음"}

Based on this data, suggest exactly 4 video topic ideas for the next upload.
Return ONLY a JSON array:
[
  {
    "title": "한국어 영상 제목 (실제 YouTube 제목 스타일, 이모지 포함, 40자 이내)",
    "category": "카테고리 (예: 카페 감성, 새벽 감성, 드라이브, 힐링, 작업용)",
    "reason": "추천 이유 (트렌드 근거 포함, 1문장, 한국어)",
    "mood": "분위기 키워드 (예: 따뜻하고 포근한)",
    "priority": "high 또는 medium"
  }
]`;

    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      messages: [{ role: "user", content: userPrompt }],
      system: systemPrompt,
    });

    const raw = (message.content[0] as { type: string; text: string }).text.trim();
    const jsonText = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();

    const topics = JSON.parse(jsonText);
    if (!Array.isArray(topics)) throw new Error("Claude did not return a JSON array");

    return new NextResponse(JSON.stringify({ topics }), {
      status: 200,
      headers: { "Content-Type": "application/json", ...corsHeaders },
    });
  } catch (error: any) {
    console.error("suggest-topics error:", error);
    return new NextResponse(
      JSON.stringify({ error: error.message || String(error) }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}
