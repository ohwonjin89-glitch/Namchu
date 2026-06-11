import { NextResponse, NextRequest } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { corsHeaders } from "@/lib/utils";

export const maxDuration = 180;
export const dynamic = "force-dynamic";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  try {
    const { topic, mood, songCount = 8, guideContent = "", extraRequest = "", channel = "Playlisttann" } = await req.json();

    const count = Math.min(Math.max(parseInt(String(songCount)), 1), 20);

    const systemPrompt = `You are an expert SUNO AI music prompt engineer specializing in Korean indie pop, city pop, and cafe-style playlists.
Your task is to generate ${count} diverse, high-quality SUNO music prompts for a YouTube playlist channel.

CRITICAL RULES:
- Every song must have DIFFERENT genre/mood/instrument combinations — no two songs should feel the same
- Mix female and male vocals across the set (aim for roughly 70% female, 30% male)
- Alternate BPM: some slow (76-88), some mid (89-100), some upbeat (101-115)
- NEVER use humming, wordless vocalizing, or long intros
- Vocals must start immediately (within first 3 seconds)
- Lyrics must be in Korean, structured with [Verse], [Pre-Chorus], [Chorus], [Bridge] sections
- Each song: exactly 8-10 lines of Korean lyrics (keep compact to avoid token overflow)
- Style prompt must be a comma-separated list of SUNO tags in English
- IMPORTANT: Keep each lyric field concise — 8 to 10 lines max. Do NOT write more.

OUTPUT FORMAT: Return ONLY a valid JSON array, no markdown, no explanation:
[{"title":"...","style":"...","lyric":"...","vocal":"여성","weird":"20%","styleVal":"75%"}]`;

    const userPrompt = `Channel: ${channel}
Topic: ${topic}
Mood/Vibe: ${mood}
Number of songs: ${count}${extraRequest ? `\nAdditional requirements: ${extraRequest}` : ""}

Prompt Guide (follow these style rules strictly):
${guideContent || "Korean indie soul, acoustic city pop, lo-fi chillhop, bossa nova, jazz-pop, acoustic R&B. BPM 88-100. Soft breathy female vocal or smooth warm male vocal."}

Generate ${count} unique SUNO music prompts. Each must feel distinct — vary the genre, tempo, instruments, and lyrical theme while staying within the ${topic} / ${mood} concept.`;

    // Use streaming to avoid "Streaming is required for operations that may take longer than 10 minutes" error
    const stream = client.messages.stream({
      model: "claude-sonnet-4-6",
      max_tokens: 32000,
      messages: [{ role: "user", content: userPrompt }],
      system: systemPrompt,
    });

    const message = await stream.finalMessage();

    const raw = (message.content[0] as { type: string; text: string }).text.trim();
    const jsonText = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();

    if (message.stop_reason === "max_tokens") {
      throw new Error(`출력 토큰 초과 — ${count}곡 요청 시 토큰이 부족합니다. 생성 곡 수를 줄이거나 서버 관리자에게 문의하세요.`);
    }

    let prompts: any;
    try {
      prompts = JSON.parse(jsonText);
    } catch (parseErr: any) {
      throw new Error(`JSON 파싱 실패 (출력이 잘렸을 수 있습니다): ${parseErr.message}`);
    }

    if (!Array.isArray(prompts)) throw new Error("Claude did not return a JSON array");

    return new NextResponse(JSON.stringify({ prompts }), {
      status: 200,
      headers: { "Content-Type": "application/json", ...corsHeaders },
    });
  } catch (error: any) {
    console.error("generate-prompts error:", error);
    return new NextResponse(
      JSON.stringify({ error: error.message || String(error) }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
