import { NextResponse, NextRequest } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import fs from "fs";
import path from "path";
import { corsHeaders } from "@/lib/utils";

export const maxDuration = 180;
export const dynamic = "force-dynamic";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 장르별 메타 (negTags + keywords — Styles는 MD 레퍼런스 파일에서 직접 사용)
const GENRE_META: Record<
  string,
  { keywords: string; negTags: string }
> = {
  "Lo-fi Focus & Cafe Chill": {
    keywords: "집중, 카페, 공부, 조용한 배경음악, 로파이 감성",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, heavy bass",
  },
  "Groove Hip-hop & Chill Pop": {
    keywords: "도시, 세련됨, 미드템포, NYC 감성, 여유 있는 리듬",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, heavy bass drop",
  },
  "Late Night R&B & Soul": {
    keywords: "늦은 밤, 이별, 감성, 드라이브, 로맨틱",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, aggressive beat",
  },
  "Upbeat City Pop & Funk Groove": {
    keywords: "밝은 에너지, 설렘, 여름, 댄서블, 긍정, 도시 활기",
    negTags:
      "kpop, bgm, humming, long intro, heavy EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, dark mood",
  },
  "Acoustic Indie Pop & Folk Soul": {
    keywords: "따뜻함, 자연, 위로, 아침 산책, 희망, 어쿠스틱",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, electric distortion",
  },
  "Chillwave & Synth Pop": {
    keywords: "몽환적, 80년대 감성, 드라이브, 신스팝",
    negTags:
      "kpop, bgm, humming, long intro, heavy EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, acoustic folk",
  },
  "Jazz-hop & Bossa Nova Chill": {
    keywords: "카페, 여유로운 오후, 재즈, 보사노바, 소박한 행복",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, heavy bass",
  },
  "Jazz Instrumental": {
    keywords: "순수 연주, 재즈 피아노 트리오, 쿨재즈, 발라드, 보사노바, 가사 없는 연주곡",
    negTags:
      "vocals, singing, lyrics, humming, ooh-ooh, la-la, mm-mm, whoa-oh, rap, spoken word, EDM drop, trap, heavy metal, kpop, electronic",
  },
};

const SECTION_MAP: Record<string, string> = {
  "Lo-fi Focus & Cafe Chill": "## 4-1.",
  "Groove Hip-hop & Chill Pop": "## 4-2.",
  "Late Night R&B & Soul": "## 4-3.",
  "Upbeat City Pop & Funk Groove": "## 4-4.",
  "Acoustic Indie Pop & Folk Soul": "## 4-5.",
  "Chillwave & Synth Pop": "## 4-6.",
  "Jazz-hop & Bossa Nova Chill": "## 4-7.",
  "Jazz Instrumental": "## 4-8.",
};

let _mdCache: string | null = null;
let _mdCacheMtime = 0;

function getMdContent(): string {
  const mdPath = path.join(process.cwd(), ".claude/agents/music-generator-genre-samples.md");
  try {
    const mtime = fs.statSync(mdPath).mtimeMs;
    if (_mdCache && mtime === _mdCacheMtime) return _mdCache;
    _mdCacheMtime = mtime;
  } catch {}
  _mdCache = fs.readFileSync(mdPath, "utf-8");
  return _mdCache;
}

function parseGenreRefs(
  mdContent: string,
  genre: string
): Array<{ refNum: number; styles: string }> {
  const sectionKey = SECTION_MAP[genre];
  if (!sectionKey) return [];

  // CRLF → LF 정규화
  const content = mdContent.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  const startIdx = content.indexOf(sectionKey);
  if (startIdx === -1) return [];

  const afterStart = content.slice(startIdx + sectionKey.length);
  const nextMatch = afterStart.search(/\n## 4-\d+\./);
  const endIdx =
    nextMatch !== -1
      ? startIdx + sectionKey.length + nextMatch
      : content.length;

  const section = content.slice(startIdx, endIdx);
  const refs: Array<{ refNum: number; styles: string }> = [];

  // 일부 레퍼런스는 "1) Styles" 헤더 없이 바로 내용이 시작됨 — (?:...)? 로 처리
  const pattern =
    /### 레퍼런스 (\d+)[\s\S]*?```\n(?:1\) Styles\n)?([\s\S]*?)\n\n*2\) Lyrics/g;

  let match;
  while ((match = pattern.exec(section)) !== null) {
    const styles = match[2].trim();
    if (styles) refs.push({ refNum: parseInt(match[1]), styles });
  }

  return refs;
}

export async function GET(req: NextRequest) {
  // /api/generate-prompts?genre=X → 장르 레퍼런스 목록 반환 (genre-refs 대체)
  try {
    const genre =
      req.nextUrl.searchParams.get("genre") ||
      "Acoustic Indie Pop & Folk Soul";
    const refs = parseGenreRefs(getMdContent(), genre);
    return new NextResponse(
      JSON.stringify({ genre, refs, count: refs.length }),
      {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      }
    );
  } catch (error: any) {
    return new NextResponse(
      JSON.stringify({ error: error.message || String(error) }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const {
      selectedGenre = "Acoustic Indie Pop & Folk Soul",
      songCount = 8,
      projectTopic = "감성 음악",
      trendVideos = [],
      extraRequest = "",
      channel = "DGM_Playlist",
      instrumental = false,
      // 대시보드에서 편집한 레퍼런스 스타일 오버라이드 (순서 보존)
      refStyles = [] as string[],
    } = await req.json();

    const count = Math.min(Math.max(parseInt(String(songCount)), 1), 99);
    const genreMeta =
      GENRE_META[selectedGenre] ||
      GENRE_META["Acoustic Indie Pop & Folk Soul"];

    // ── 레퍼런스 풀 결정 ──────────────────────────────────────
    // 대시보드가 refStyles를 보내면 그것을 사용, 아니면 MD 파일에서 파싱
    let refs: { refNum: number; styles: string }[];
    if (refStyles && refStyles.length > 0) {
      refs = refStyles.map((s: string, i: number) => ({
        refNum: i + 1,
        styles: s,
      }));
    } else {
      refs = parseGenreRefs(getMdContent(), selectedGenre);
    }

    if (refs.length === 0) {
      throw new Error(
        `"${selectedGenre}" 장르의 레퍼런스를 찾을 수 없습니다. music-generator-genre-samples.md를 확인해주세요.`
      );
    }

    // ── 곡별 사전 배정 ────────────────────────────────────────
    // 레퍼런스 라운드로빈: 모든 곡에 대해 i % refs.length → refs 개수보다 곡이 많아도 랜덤 없이 순환
    const assignments = Array.from({ length: count }, (_, i) => {
      const refIdx = i % refs.length;
      return {
        idx: i + 1,
        refNum: refs[refIdx].refNum,
        refStyles: refs[refIdx].styles,
        vocalGender: i % 2 === 0 ? "female" : "male",
        vocal: i % 2 === 0 ? "여성" : "남성",
        styleGroup: i % 3 === 0 ? "anchor" : "variation",
        weirdness: i % 3 === 0 ? 12 : 14 + Math.floor(Math.random() * 8),
        styleInfluence: 65 + Math.floor(Math.random() * 16),
      };
    });

    const trendContext =
      trendVideos.length > 0
        ? `Trending Korean YouTube videos this week (use for scene inspiration):\n${trendVideos
            .slice(0, 5)
            .map(
              (v: any) =>
                `- "${v.title || ""}" (${Math.round(
                  (v.viewCount || v.views || 0) / 10000
                )}만 조회)`
            )
            .join("\n")}`
        : "";

    // ── Claude에게 Lyrics(or Instrumental 설명)만 요청 ──────────
    const systemPrompt = instrumental
      ? `You are a DGM YouTube playlist music director. Your job is to write SUNO SECTION STRUCTURE for instrumental tracks targeting ~3 minutes.
The musical Style/tags are ALREADY FIXED from reference tracks — do NOT write or modify them.

INSTRUMENTAL STRUCTURE RULES:
- Use exactly 7 Suno section tags in this order: [Intro] [Section A] [Section B] [Section C] [Bridge] [Section D] [Outro]
- Under EACH section tag, write [INSTRUMENTAL] on the next line, then a 1-sentence atmosphere note (10–15 words max)
- Each section must have a distinct emotional/atmospheric character — no repetition across sections
- NO lyrics, NO vocal directions, NO singing whatsoever — pure instrumental guidance only
- Write in English only`
      : `You are a DGM YouTube playlist lyricist. Your only job is to write ENGLISH LYRICS for each song.
The musical Style/tags are ALREADY FIXED from reference tracks — do NOT write or modify them.

LYRICS RULES (DGM standard):
- English lyrics only, approximately 3 minutes total per song
- Structure MUST follow: [Intro][Verse 1][Pre-Chorus][Chorus][Verse 2][Pre-Chorus][Chorus][Bridge][Final Chorus][Outro]
- First lyric line must start within 3 seconds — no long wordless introductions
- ZERO tolerance: humming, ooh-ooh, la-la, mm-mm, whoa-oh, meaningless vocal ad-libs
- Do NOT directly mention the project topic word — express it through scene imagery only
- Each song MUST have a completely different scene, moment, and emotional situation
- No direct imitation of any existing artist or song`;

    const songList = assignments
      .map(
        (a) =>
          `Song ${a.idx} (ref ${a.refNum}${instrumental ? ", INSTRUMENTAL" : `, vocal: ${a.vocalGender}`}, styleGroup: ${a.styleGroup}):
Style/tags context (DO NOT change, use as musical reference only):
"${a.refStyles}"
→ ${instrumental
    ? "Write 7-section Suno structure: [Intro]/[Section A]/[Section B]/[Section C]/[Bridge]/[Section D]/[Outro] — each with [INSTRUMENTAL] + 1-sentence note. Target ~3 minutes. No lyrics, no vocals."
    : "Write ONLY fresh English lyrics with the above atmosphere in mind."}`
      )
      .join("\n\n");

    const userPrompt = `Project topic: ${projectTopic}
Genre: ${selectedGenre} (${genreMeta.keywords})
${trendContext ? trendContext + "\n" : ""}${extraRequest ? `Extra requirements (PRIORITY — override default rules if conflicting): ${extraRequest}\n` : ""}
${instrumental ? "Generate instrumental atmosphere descriptions" : "Write lyrics"} for ${count} songs. Each must explore a completely different scene or emotional moment inspired by the project topic.

${songList}

Return ONLY a valid JSON array (no markdown, no explanation):
[{
  "idx": 1,
  "title": "English song title",
  "scene": "장면 설명 15자 이내 한국어",
  "lyric": "${instrumental ? "7-section Suno structure: [Intro]\\n[INSTRUMENTAL] note\\n\\n[Section A]\\n[INSTRUMENTAL] note\\n...\\n[Outro]\\n[INSTRUMENTAL] note" : "full English lyrics with all section tags [Intro][Verse 1]..."}"
}]`;

    const stream = client.messages.stream({
      model: "claude-sonnet-4-6",
      max_tokens: 32000,
      messages: [{ role: "user", content: userPrompt }],
      system: systemPrompt,
    });

    const message = await stream.finalMessage();

    if (message.stop_reason === "max_tokens") {
      throw new Error(
        `출력 토큰 초과 — ${count}곡 요청 시 토큰이 부족합니다. 생성 곡 수를 줄여주세요.`
      );
    }

    const raw = (
      message.content[0] as { type: string; text: string }
    ).text.trim();
    const jsonText = raw
      .replace(/^```(?:json)?\s*/i, "")
      .replace(/\s*```$/i, "")
      .trim();

    let claudeResults: any[];
    try {
      claudeResults = JSON.parse(jsonText);
    } catch (parseErr: any) {
      throw new Error(`JSON 파싱 실패: ${parseErr.message}`);
    }

    if (!Array.isArray(claudeResults))
      throw new Error("Claude did not return a JSON array");

    // ── 레퍼런스 Styles + Claude Lyrics 합산 ─────────────────
    const prompts = claudeResults.map((c: any, i: number) => {
      const a = assignments[i] || assignments[assignments.length - 1];
      return {
        title: c.title || `Track ${i + 1}`,
        style: a.refStyles,          // 레퍼런스 Styles 원문 → Suno tags로 사용
        lyric: c.lyric || "",        // Claude가 쓴 Lyrics → Suno prompt로 사용
        scene: c.scene || "",
        vocal: a.vocal,
        vocalGender: a.vocalGender,
        styleGroup: a.styleGroup,
        weird: a.weirdness,
        styleVal: a.styleInfluence,
        negativeTags: genreMeta.negTags,
        refNum: a.refNum,
      };
    });

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
