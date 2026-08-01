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
  "Old Jazz": {
    keywords: "빈티지, 올드재즈, 스윙, 축음기 감성, 클래식 재즈보컬, 1940~1950년대 무드, 강한 LP 레코드/바이닐 크랙클과 축음기 서피스 노이즈 질감(또렷하게 들릴 정도), 묵직하고 진중한 톤(발랄함 지양)",
    negTags:
      "kpop, bgm, humming, long intro, EDM drop, ooh-ooh, la-la, mm-mm, whoa-oh, trap, synth, electronic, heavy bass drop, modern pop production, upbeat cheerful bouncy energy, bright pop energy, clean pristine studio mix, digital clarity",
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
  "Old Jazz": "## 4-9.",
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
      // "synthesize"(기본값, 2026-08-01부터) = 레퍼런스를 학습 예시 삼아 AI가 매번 새 Styles를 합성 생성
      // "reference" = 레퍼런스 Styles 원문을 거의 그대로 사용 (명시적으로 지정해야만 적용)
      // 예전 기본값("reference")은 레퍼런스 문장을 그대로 복사해 쓰다 보니, 레퍼런스 풀보다
      // 요청 곡 수가 많은 배치에서 여러 곡이 사실상 동일한 인트로/아웃로/리듬으로 들리는
      // 사고로 이어졌다(2026-07-30, 프로젝트 2026072901). "레퍼런스를 참고해 AI가 창작"하는
      // 쪽을 기본값으로 바꾸고, 레퍼런스 배정 자체는 여전히 라운드 단위로 골고루 순환시켜
      // 등록된 레퍼런스가 모두 균등하게 창작의 씨앗으로 쓰이도록 한다.
      styleMode = "synthesize" as "reference" | "synthesize",
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
    // 레퍼런스 풀을 "라운드" 단위로 소진한다: 매 라운드마다 전체 레퍼런스를 새로
    // 셔플해서 1:1로 중복 없이 배정하고, count가 refs.length를 초과하면 다음
    // 라운드로 넘어가 다시 전체를 셔플한다. (예: refs=10, count=15 → 1라운드는
    // 10개 전부 1회씩, 2라운드는 그중 5개를 다시 랜덤 순서로 사용)
    // 이전 방식(초과분을 매번 독립적으로 완전 무작위 추첨)은 같은 레퍼런스가
    // 초과분끼리도 중복될 수 있었고, 무엇보다 재사용된 곡의 Styles 텍스트를
    // 전혀 변형하지 않아 "보컬 성별 단어만 다르고 나머지는 완전히 동일한 곡"이
    // 한 프로젝트 안에 여러 쌍 생기는 사고로 이어졌다(2026-07-30, 프로젝트
    // 2026072901 — 15곡 중 10곡이 5쌍으로 Styles 완전 중복, 인트로/아웃로/
    // 리듬이 사실상 같은 곡이 되어 영상 전체 폐기). 아래 forceVary 플래그로
    // 재사용 곡은 반드시 Styles를 새로 변주하도록 강제해 재발을 막는다.
    const refSequence: typeof refs = [];
    for (let round = 0; round * refs.length < count; round++) {
      refSequence.push(...[...refs].sort(() => Math.random() - 0.5));
    }
    const assignments = Array.from({ length: count }, (_, i) => {
      const ref = refSequence[i];
      return {
        idx: i + 1,
        refNum: ref.refNum,
        refStyles: ref.styles,
        // 이 프로젝트 배치 안에서 레퍼런스 풀을 이미 한 바퀴 이상 소진하고
        // 재사용되는 곡 — Styles를 그대로 베끼지 않고 새로 변주해야 한다.
        forceVary: i >= refs.length,
        vocalGender: i % 2 === 0 ? "female" : "male",
        vocal: i % 2 === 0 ? "여성" : "남성",
        styleGroup: i % 3 === 0 ? "anchor" : "variation",
        weirdness: i % 3 === 0 ? 12 : 14 + Math.floor(Math.random() * 8),
        styleInfluence: 65 + Math.floor(Math.random() * 16),
      };
    });
    const anyForceVary = assignments.some((a) => a.forceVary);

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

    // ── Claude에게 Lyrics(or Instrumental 설명)만 요청 (+ synthesize 모드면 Styles도 요청) ──
    const isSynthesize = styleMode === "synthesize";

    const styleSynthesisInstructions = isSynthesize
      ? `

STYLE SYNTHESIS MODE (also write a NEW "style" field per song):
You are also given several EXAMPLE reference styles below (§ "Reference style examples for this genre").
Study them to learn the genre's recurring elements — instrumentation, the role of guitar/piano/synth, bass character,
drum pattern, vocal tone, arrangement flow (verse→chorus), chorus character, tempo (BPM) range, key hints, and mix texture.
Then WRITE A BRAND-NEW original "style" description per song — do NOT copy any example sentence verbatim, do NOT just
reshuffle words from one example. Recombine and vary the learned elements (different instrument pairing, a shifted BPM
within the genre's plausible range, a different mix texture) so each song sounds like an authentic but distinct member
of the same genre family. Stay strictly within instrumentation/mood that fits this genre — do not introduce elements
foreign to it (e.g. no synth pads in a genre defined by acoustic guitar, unless an example already uses it).
The "style" field MUST be full prose (a paragraph of complete sentences), never a keyword list, and must NOT contain
any negative/exclusionary phrasing (that belongs only in negative_tags, which is fixed separately).`
      : "";

    // count가 레퍼런스 수를 초과해 일부 곡이 같은 레퍼런스를 재사용할 때(forceVary),
    // styleMode가 "reference"라도 그 곡들만은 Styles를 새로 변주해서 쓰게 강제한다.
    // 그대로 두면 같은 프로젝트 안에 Styles가 통째로(보컬 성별만 다르고) 겹치는 곡이
    // 생긴다(2026-07-30 사고, 위 refSequence 주석 참고).
    const forceVaryInstructions =
      !isSynthesize && anyForceVary
        ? `

REUSED-REFERENCE SONGS (marked "NEEDS NEW STYLE" below): this batch requested more songs than this genre has unique
reference styles, so a few songs were assigned a reference already used by an earlier song in this same batch. For
those songs ONLY, also write a NEW "style" field: study the given reference's instrumentation, BPM, and mood, then
write a fresh prose description that keeps the same genre feel but varies at least the instrument pairing, BPM
(±5-10 within the genre's plausible range), and mix texture — so it does not sound identical to the reference or to
the other song(s) reusing it. Do NOT copy the reference sentence verbatim. Stay strictly within this genre's
instrumentation/mood family. For every other song (not marked "NEEDS NEW STYLE"), use the given reference Style/tags
exactly as-is and do NOT write a "style" field for it.`
        : "";

    const systemPrompt = instrumental
      ? `You are a DGM YouTube playlist music director. Your job is to write SUNO SECTION STRUCTURE for instrumental tracks targeting ~3 minutes.
${isSynthesize ? "You also synthesize a fresh Style description per song (see STYLE SYNTHESIS MODE below)." : anyForceVary ? "The musical Style/tags are FIXED from reference tracks for most songs — but see REUSED-REFERENCE SONGS below for the exceptions." : "The musical Style/tags are ALREADY FIXED from reference tracks — do NOT write or modify them."}

INSTRUMENTAL STRUCTURE RULES:
- Use exactly 7 Suno section tags in this order: [Intro] [Section A] [Section B] [Section C] [Bridge] [Section D] [Outro]
- Under EACH section tag, write [INSTRUMENTAL] on the next line, then a 1-sentence atmosphere note (10–15 words max)
- Each section must have a distinct emotional/atmospheric character — no repetition across sections
- NO lyrics, NO vocal directions, NO singing whatsoever — pure instrumental guidance only
- Write in English only${styleSynthesisInstructions}${forceVaryInstructions}`
      : `You are a DGM YouTube playlist lyricist. Your only job is to write ENGLISH LYRICS for each song.
${isSynthesize ? "You also synthesize a fresh Style description per song (see STYLE SYNTHESIS MODE below)." : anyForceVary ? "The musical Style/tags are FIXED from reference tracks for most songs — but see REUSED-REFERENCE SONGS below for the exceptions." : "The musical Style/tags are ALREADY FIXED from reference tracks — do NOT write or modify them."}

LYRICS RULES (DGM standard):
- English lyrics only, approximately 3 minutes total per song
- Structure MUST follow: [Intro][Verse 1][Pre-Chorus][Chorus][Verse 2][Pre-Chorus][Chorus][Bridge][Final Chorus][Outro]
- First lyric line must start within 3 seconds — no long wordless introductions
- ZERO tolerance: humming, ooh-ooh, la-la, mm-mm, whoa-oh, meaningless vocal ad-libs
- Do NOT directly mention the project topic word — express it through scene imagery only
- Each song MUST have a completely different scene, moment, and emotional situation
- No direct imitation of any existing artist or song${styleSynthesisInstructions}${forceVaryInstructions}`;

    const songList = assignments
      .map((a) => {
        const needsNewStyle = isSynthesize || a.forceVary;
        return `Song ${a.idx} (ref ${a.refNum}${instrumental ? ", INSTRUMENTAL" : `, vocal: ${a.vocalGender}`}, styleGroup: ${a.styleGroup})${a.forceVary && !isSynthesize ? " [NEEDS NEW STYLE — reused reference]" : ""}:
${needsNewStyle
    ? `Nearest reference style (inspiration only — do NOT copy, synthesize a NEW style per the rules above):\n"${a.refStyles}"`
    : `Style/tags context (DO NOT change, use as musical reference only):\n"${a.refStyles}"`}
→ ${instrumental
    ? `Write 7-section Suno structure: [Intro]/[Section A]/[Section B]/[Section C]/[Bridge]/[Section D]/[Outro] — each with [INSTRUMENTAL] + 1-sentence note. Target ~3 minutes. No lyrics, no vocals.${needsNewStyle ? " Also write a new \"style\" field." : ""}`
    : `Write ONLY fresh English lyrics with the above atmosphere in mind.${needsNewStyle ? " Also write a new \"style\" field." : ""}`}`;
      })
      .join("\n\n");

    // synthesize 모드일 때 장르 전체 스타일 범위를 보여주는 참고 예시(최대 5개, 랜덤 샘플)
    const inspirationBlock = isSynthesize
      ? `\nReference style examples for this genre (study the recurring elements, then write NEW styles — never copy these verbatim):\n${[...refs]
          .sort(() => Math.random() - 0.5)
          .slice(0, Math.min(5, refs.length))
          .map((r, i) => `Example ${i + 1}: "${r.styles}"`)
          .join("\n")}\n`
      : "";

    const userPrompt = `Project topic: ${projectTopic}
Genre: ${selectedGenre} (${genreMeta.keywords})
${trendContext ? trendContext + "\n" : ""}${extraRequest ? `Extra requirements (PRIORITY — override default rules if conflicting): ${extraRequest}\n` : ""}
${instrumental ? "Generate instrumental atmosphere descriptions" : "Write lyrics"} for ${count} songs. Each must explore a completely different scene or emotional moment inspired by the project topic.
${inspirationBlock}
${songList}

Return ONLY a valid JSON array (no markdown, no explanation):
[{
  "idx": 1,
  "title": "English song title",
  "scene": "장면 설명 15자 이내 한국어",
  ${isSynthesize || anyForceVary ? `"style": "new synthesized Style prose — ONLY for songs marked NEEDS NEW STYLE (or all songs in STYLE SYNTHESIS MODE); omit this field entirely for other songs",\n  ` : ""}"lyric": "${instrumental ? "7-section Suno structure: [Intro]\\n[INSTRUMENTAL] note\\n\\n[Section A]\\n[INSTRUMENTAL] note\\n...\\n[Outro]\\n[INSTRUMENTAL] note" : "full English lyrics with all section tags [Intro][Verse 1]..."}"
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
      // synthesize(기본값, 2026-08-01~): AI가 매 곡 자신에게 배정된 레퍼런스(round-robin으로
      //   전체 풀을 균등 순환)를 참고해 새로 합성한 Styles 사용 — 원문 복사 금지
      // reference(명시적 요청 시): 레퍼런스 Styles 원문 그대로 사용
      // forceVary(레퍼런스 재사용 곡, reference 모드에서만 발생): reference 모드라도 AI가
      //   새로 변주한 Styles를 사용 — 그대로 두면 같은 프로젝트 안에 Styles가 통째로 겹치는
      //   곡이 생긴다(2026-07-30 사고)
      const useVariedStyle = (isSynthesize || a.forceVary) && c.style;
      return {
        title: c.title || `Track ${i + 1}`,
        style: useVariedStyle ? c.style : a.refStyles,
        styleMode: isSynthesize ? "synthesize" : a.forceVary ? "reference+varied" : "reference",
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

    const countMismatch = claudeResults.length !== count;
    return new NextResponse(JSON.stringify({
      prompts,
      ...(countMismatch ? { warning: `요청 곡 수(${count})와 Claude 응답 곡 수(${claudeResults.length})가 다릅니다. 트랙 수 부족이 발생할 수 있습니다.` } : {}),
    }), {
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
