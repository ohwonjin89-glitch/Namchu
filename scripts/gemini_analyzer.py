#!/usr/bin/env python3
"""
Gemini API로 YouTube 영상을 분석하여 DGM 프롬프트 가이드를 생성합니다.

Usage:
  python3 scripts/gemini_analyzer.py setup-genre <장르명> <youtube_url>
      → 영상에서 곡을 직접 감지(최대 5곡) → 해당 장르의 영구 레퍼런스 저장

  python3 scripts/gemini_analyzer.py add-curated <장르명> <url1> [<url2> ...]
      → 개별 곡 URL 여러 개를 각각 분석 → 해당 장르의 영구 레퍼런스로 일괄 추가

  python3 scripts/gemini_analyzer.py analyze <youtube_url> [<youtube_url> ...]
      → 주간 트렌드 분석 (교체형 레퍼런스 생성)

  python3 scripts/gemini_analyzer.py list-genres
      → 현재 등록된 장르 목록

  python3 scripts/gemini_analyzer.py update-db
      → style-database.json 통계 출력

환경변수:
  GEMINI_API_KEY   Google AI Studio에서 발급한 API 키
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows cp949 환경에서 이모지 출력 가능하도록 UTF-8 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    print("❌ google-genai 패키지 없음. 설치: pip install google-genai")
    sys.exit(1)

# ── 경로 설정 ────────────────────────────────────────────
# 배포 서버가 바뀔 때마다(RunPod → VPS 등) 하드코딩 경로를 추가하는 대신,
# 이 스크립트가 위치한 저장소 루트를 스스로 찾는다 (scripts/의 부모 디렉토리).
PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_DIR / ".claude" / "agents"
GENRE_SAMPLES_PATH = AGENTS_DIR / "music-generator-genre-samples.md"
STYLE_DB_PATH = AGENTS_DIR / "style-database.json"
BACKUP_DIR = AGENTS_DIR / "backups"

# ── 레퍼런스 한도 ────────────────────────────────────────
MAX_CURATED_REFS = 19  # 기본샘플 1개 포함 시 총 20개

# ── 기존 장르 목록 ───────────────────────────────────────
EXISTING_GENRES = [
    "Lo-fi Focus & Cafe Chill",
    "Groove Hip-hop & Chill Pop",
    "Late Night R&B & Soul",
    "Upbeat City Pop & Funk Groove",
    "Acoustic Indie Pop & Folk Soul",
    "Chillwave & Synth Pop",
    "Jazz-hop & Bossa Nova Chill",
]

# ── 우리 채널 성격 필터 ──────────────────────────────────
FILTER_CRITERIA = """
아래에 해당하면 filter_out: true로 표시하고 filter_reason을 작성해줘:
1. 가사 없는 순수 BGM (instrumental only, no lyrics)
2. KPOP / K-pop 장르 (아이돌, 댄스 팝, 밝고 신나는 K-pop)
3. 어린이 동요, 클래식 연주, EDM, 록 (우리 채널 감성과 무관)

우리 채널 성격:
- 감성적이고 서정적인 팝/소울/재즈/인디
- 한국어 또는 영어 가사 있는 곡
- 20~35세 타깃, 늦은 밤/카페/드라이브 감성
"""

# ── setup-genre 프롬프트 (곡 자동 감지 + 분석) ───────────
SETUP_GENRE_PROMPT = """
이 YouTube 영상을 직접 듣고 분석해줘. JSON 외의 텍스트 없이 JSON만 출력해.

=== 작업 순서 ===
1. 영상에서 재생되는 개별 곡들을 순서대로 감지한다.
   - 곡 경계 판단 기준: 무음 구간, 박수/환호, 분위기 전환, 새 인트로 시작 등
   - 고정된 시간(3분, 6분 등)으로 자르지 말고, 실제 음악을 들어서 곡이 바뀌는 시점을 찾을 것
2. 1번 곡부터 최대 5번 곡까지 각각 분석한다.
3. 아래 JSON 형식 그대로 출력한다.

=== 스타일 작성 규칙 ===
반드시 완성된 영어 문장형으로 작성. 단어 나열 금지.
포함 필수 요소: 장르명, 서브장르, 주요 악기, 드럼 패턴, 베이스 스타일, 보컬 성별/톤, BPM, Key, 믹스 텍스처

좋은 예시:
"Lo-fi hip-hop with a warm cafe ambiance. A soft female vocal leads with an airy, breathy tone.
Mellow piano chords provide harmonic warmth, layered with soft vinyl-textured drums at 84 BPM in 4/4 time in A minor.
A plucked acoustic bass holds the low end. The mix has a warm, slightly dusty texture."

=== 가사 구조 규칙 ===
구조: [Intro] → [Verse 1] → [Pre-Chorus] → [Chorus] → [Verse 2] → [Pre-Chorus] → [Chorus] → [Bridge] → [Final Chorus] → [Outro]
길이: Intro 1~2줄 / Verse 4~6줄 / Pre-Chorus 2~4줄 / Chorus 4~6줄 / Bridge 4~6줄 / Final Chorus 6~8줄 / Outro 2~4줄
언어: 영어 가사로 작성
금지: 주제 단어 직접 언급 금지 (카페 주제→coffee/cafe 금지, 드라이브→drive 금지 등)
      humming, ooh-ooh, la-la, mm-mm 등 의미없는 애드리브 금지

=== 출력 JSON 형식 ===
{{
  "source_url": "{url}",
  "genre_name": "{genre_name}",
  "songs": [
    {{
      "track_number": 1,
      "detected_start": "0:00",
      "detected_end": "3:24",
      "styles": "1) Styles\\n[완성된 영어 문장형 스타일 설명]",
      "lyrics_structure": "2) Lyrics\\n[Hook]\\n[가사]\\n\\n[Verse 1]\\n[악기/지시어]\\n[가사]\\n\\n[Pre-Chorus]\\n[지시어]\\n[가사]\\n\\n[Chorus]\\n[지시어]\\n[가사]\\n\\n[Verse 2]\\n[지시어]\\n[가사]\\n\\n[Pre-Chorus]\\n[지시어]\\n[가사]\\n\\n[Chorus]\\n[지시어]\\n[가사]\\n\\n[Bridge]\\n[지시어]\\n[가사]\\n\\n[Final Chorus]\\n[지시어]\\n[가사]\\n\\n[Outro]\\n[지시어]\\n[가사]",
      "vocal_gender": "female",
      "vocal_tone": "허스키/맑은/따뜻한/몽환적/청량한 중 하나",
      "bpm": 84,
      "image_keywords": "Midjourney 영어 프롬프트 20단어 이내 배경이미지용",
      "image_palette": "색상 팔레트 한국어 2~3가지",
      "image_style": "이미지 분위기 1문장 한국어"
    }}
  ]
}}
"""

# ── analyze 단일 영상 프롬프트 (주간 트렌드용) ───────────
ANALYSIS_PROMPT = """
이 YouTube 영상의 음악을 분석해서 아래 JSON 형식 그대로 출력해줘.
JSON 외의 다른 텍스트 없이 JSON만 출력해.

⚠️ 중요: 영상의 앞부분에서 첫 번째 곡만 분석할 것.
   Gemini가 직접 듣고 첫 번째 곡의 끝을 판단한 뒤 그 곡만 대상으로 한다.

=== 제외 기준 ===
{filter_criteria}

=== 기존 장르 목록 ===
{existing_genres}

=== 출력 JSON 형식 ===
{{
  "filter_out": false,
  "filter_reason": "",
  "genre_name": "기존 장르명 or 새 장르명 (영어)",
  "genre_name_ko": "장르명 한국어",
  "is_new_genre": false,
  "styles": "1) Styles\\n[장르명, 주요 악기, 보컬 성별/톤, BPM, 분위기를 완성된 영어 문장으로]",
  "lyrics_structure": "2) Lyrics\\n[Hook]\\n[가사]\\n\\n[Verse 1]\\n[지시어]\\n[가사]\\n\\n[Pre-Chorus]\\n[지시어]\\n[가사]\\n\\n[Chorus]\\n[지시어]\\n[가사]\\n\\n[Verse 2]\\n[지시어]\\n[가사]\\n\\n[Bridge]\\n[지시어]\\n[가사]\\n\\n[Outro]\\n[지시어]\\n[가사]",
  "vocal_gender": "female",
  "vocal_tone": "허스키/맑은/따뜻한/몽환적/청량한 중 하나",
  "bpm": 80,
  "image_keywords": "Midjourney 영어 프롬프트 20단어 이내",
  "image_palette": "색상 팔레트 한국어 2~3가지",
  "image_style": "이미지 분위기 1문장 한국어"
}}

YouTube URL: {url}
"""


# ── DB 로드/저장 ─────────────────────────────────────────
def load_style_db() -> dict:
    if STYLE_DB_PATH.exists():
        with open(STYLE_DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "1.0",
        "last_updated": None,
        "analyzed_count": 0,
        "genres": {},
        "filtered_out": [],
        "new_genres": []
    }


def save_style_db(db: dict):
    db["last_updated"] = datetime.now().isoformat()
    STYLE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STYLE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_client() -> object:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


# ── setup-genre: 영상에서 곡 자동 감지 후 영구 레퍼런스 생성 ──
def analyze_genre_setup(genre_name: str, url: str, client) -> dict | None:
    """YouTube 영상에서 곡을 자동 감지해서 최대 5개 프롬프트 생성."""
    prompt = SETUP_GENRE_PROMPT.format(genre_name=genre_name, url=url)

    try:
        print(f"  Gemini가 영상을 듣고 곡을 감지 중...")
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                {
                    "file_data": {
                        "file_uri": url,
                        "mime_type": "video/*"
                    }
                },
                prompt
            ]
        )
        raw = response.text.strip()

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            print(f"  ❌ JSON 파싱 실패: {raw[:300]}")
            return None

        result = json.loads(json_match.group())
        result["analyzed_at"] = datetime.now().isoformat()
        return result

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Gemini API 오류: {e}")
        return None


def save_curated_references(genre_name: str, url: str, songs: list):
    """
    분석된 곡들을 music-generator-genre-samples.md의 해당 장르에 영구 레퍼런스로 저장.
    source: user_curated 태그로 보호 (주간 트렌드 교체 불가).
    """
    if not GENRE_SAMPLES_PATH.exists():
        print(f"  ❌ 장르 샘플 파일 없음: {GENRE_SAMPLES_PATH}")
        return 0

    content = GENRE_SAMPLES_PATH.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    saved_count = 0

    # 해당 장르 섹션 뒤에 레퍼런스 블록 삽입
    # 장르 섹션 헤더 패턴: ## 4-N. {genre_name}
    genre_pattern = re.escape(genre_name)
    section_match = re.search(
        rf'(## \d+-\d+\. [^\n]*{genre_pattern}[^\n]*\n)',
        content,
        re.IGNORECASE
    )

    if not section_match:
        print(f"  ❌ '{genre_name}' 장르 섹션을 찾을 수 없습니다.")
        print(f"     파일에서 정확한 장르명을 확인하세요: {GENRE_SAMPLES_PATH}")
        return 0

    insert_pos = section_match.end()

    # 기존 user_curated 블록이 있으면 제거 후 새로 삽입
    existing_block = re.search(
        r'\n<!-- CURATED_REFS_START -->[\s\S]*?<!-- CURATED_REFS_END -->\n?',
        content[insert_pos:]
    )
    if existing_block:
        start = insert_pos + existing_block.start()
        end = insert_pos + existing_block.end()
        content = content[:start] + content[end:]

    # 기존 샘플 코드블록(``` ... ```) 뒤에 삽입 (기본샘플 먼저, refs 나중)
    code_block_m = re.search(r'```[\s\S]*?```', content[insert_pos:])
    if code_block_m:
        insert_pos = insert_pos + code_block_m.end()

    # 새 레퍼런스 블록 생성
    blocks = [f"\n<!-- CURATED_REFS_START -->\n"]
    blocks.append(f"> 🎵 영구 레퍼런스 (user_curated) — 원본 영상: {url} / 분석일: {today}\n\n")

    for song in songs[:5]:
        n = song.get("track_number", saved_count + 1)
        start_t = song.get("detected_start", "?")
        end_t = song.get("detected_end", "?")
        styles = song.get("styles", "")
        lyrics = song.get("lyrics_structure", "")

        blocks.append(f"### 레퍼런스 {n} ({start_t} ~ {end_t})\n\n")
        blocks.append(f"```\n{styles}\n\n{lyrics}\n```\n\n")
        saved_count += 1

    blocks.append("<!-- CURATED_REFS_END -->\n")

    # 섹션 헤더 바로 뒤에 삽입
    curated_block = "".join(blocks)
    content = content[:insert_pos] + curated_block + content[insert_pos:]
    GENRE_SAMPLES_PATH.write_text(content, encoding="utf-8")

    return saved_count


def cmd_setup_genre(genre_name: str, url: str):
    """
    사용자가 지정한 YouTube 영상에서 1~5번 곡을 자동 감지해서
    해당 장르의 영구 레퍼런스(user_curated) 5개를 생성한다.
    """
    if genre_name not in EXISTING_GENRES:
        print(f"⚠ '{genre_name}'은 등록된 장르가 아닙니다.")
        print("  등록된 장르:")
        for g in EXISTING_GENRES:
            print(f"    - {g}")
        print("\n정확한 장르명을 입력하거나, 장르 추가가 필요하면 analyze 커맨드를 사용하세요.")
        sys.exit(1)

    print(f"\n🎵 setup-genre: {genre_name}")
    print(f"   영상: {url}")
    print(f"   Gemini가 영상을 직접 듣고 곡 경계를 감지합니다...\n")

    client = get_client()
    result = analyze_genre_setup(genre_name, url, client)

    if result is None:
        print("❌ 분석 실패")
        sys.exit(1)

    songs = result.get("songs", [])
    if not songs:
        print("❌ 감지된 곡이 없습니다.")
        sys.exit(1)

    print(f"\n✅ {len(songs)}곡 감지 완료:")
    for song in songs:
        n = song.get("track_number", "?")
        s = song.get("detected_start", "?")
        e = song.get("detected_end", "?")
        vocal = song.get("vocal_gender", "?")
        bpm = song.get("bpm", "?")
        print(f"  {n}번곡  {s} ~ {e}  |  {vocal}  {bpm}BPM")

    saved = save_curated_references(genre_name, url, songs)
    print(f"\n✅ {saved}개 영구 레퍼런스 저장 완료")
    print(f"   파일: {GENRE_SAMPLES_PATH}")
    print(f"   태그: user_curated (주간 트렌드 교체로부터 보호됨)")

    # style-database에도 기록
    db = load_style_db()
    db["analyzed_count"] += len(songs)
    if genre_name not in db["genres"]:
        db["genres"][genre_name] = {"name_ko": genre_name, "is_new": False, "samples": []}
    for song in songs:
        db["genres"][genre_name]["samples"].append({
            "source_url": url,
            "source": "user_curated",
            "track_number": song.get("track_number"),
            "detected_start": song.get("detected_start"),
            "detected_end": song.get("detected_end"),
            "analyzed_at": result["analyzed_at"],
            "vocal_gender": song.get("vocal_gender"),
            "vocal_tone": song.get("vocal_tone"),
            "bpm": song.get("bpm"),
        })
    save_style_db(db)


# ── add-curated: 개별 URL 배치 분석 후 영구 레퍼런스 저장 ──

def _section_end(content: str, after_pos: int) -> int:
    """현재 섹션의 끝 위치 반환 (다음 --- 또는 ## 헤더 직전)."""
    m = re.search(r'\n---\n|\n## ', content[after_pos:])
    return after_pos + m.start() if m else len(content)


def _extract_existing_curated_refs(content: str, after_pos: int) -> list[dict]:
    """현재 섹션 내 CURATED_REFS 블록에서 기존 레퍼런스들을 파싱해 반환."""
    end = _section_end(content, after_pos)
    section = content[after_pos:end]
    block_m = re.search(
        r'<!-- CURATED_REFS_START -->([\s\S]*?)<!-- CURATED_REFS_END -->',
        section
    )
    if not block_m:
        return []
    block = block_m.group(1)
    refs = []
    ref_header = "### 레퍼런스 "
    parts = block.split(ref_header)[1:]
    for part in parts:
        lines = part.split("\n", 1)
        rest = lines[1] if len(lines) > 1 else ""
        url = ""
        url_prefix = "> 원본: "
        if rest.lstrip().startswith(url_prefix):
            rest_stripped = rest.lstrip()
            url_end = rest_stripped.index("\n")
            url = rest_stripped[len(url_prefix):url_end].strip()
            rest = rest_stripped[url_end + 1:]
        code_m = re.search(r"```([\s\S]*?)```", rest)
        if code_m:
            refs.append({"source_url": url, "content": code_m.group(1).strip()})
    return refs


def _claude_pick_weakest_ref(genre_name: str, all_refs: list[dict]) -> int:
    """
    Claude API로 채널 감성과 가장 거리 먼 레퍼런스 1개의 인덱스를 선택.
    실패 시 가장 오래된(첫 번째) 레퍼런스 반환.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()
        previews = ""
        for i, ref in enumerate(all_refs):
            preview = ref.get("content", "")[:300].replace("\n", " ")
            previews += f"\n[{i+1}] {ref.get('source_url', '')}\n{preview}\n"

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": (
                    f"음악 큐레이터로서 판단해줘.\n"
                    f"채널: 감성적/서정적 팝·소울·재즈·인디, 20~35세, 카페/드라이브/늦은밤.\n"
                    f"장르: {genre_name}\n\n"
                    f"아래 중 채널 감성과 가장 거리 먼 것 1개 번호만 출력:\n{previews}"
                )
            }]
        )
        num_m = re.search(r'\d+', msg.content[0].text.strip())
        if num_m:
            idx = int(num_m.group()) - 1
            if 0 <= idx < len(all_refs):
                return idx
    except Exception as e:
        print(f"  ⚠ Claude 판단 실패, 가장 오래된 레퍼런스 제거: {e}")
    return 0


def save_curated_references_batch(genre_name: str, songs: list) -> int:
    """
    여러 개별 URL에서 분석된 곡들을 해당 장르의 user_curated 블록에 저장.
    - 기존 레퍼런스와 합산해 MAX_CURATED_REFS(19개) 초과 시 AI가 가장 약한 것 제거.
    - songs 각 항목에 source_url 필드가 있어야 함.
    """
    if not GENRE_SAMPLES_PATH.exists():
        print(f"  ❌ 장르 샘플 파일 없음: {GENRE_SAMPLES_PATH}")
        return 0

    content = GENRE_SAMPLES_PATH.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    saved_count = 0

    genre_pattern = re.escape(genre_name)
    section_match = re.search(
        rf'(## \d+-\d+\. [^\n]*{genre_pattern}[^\n]*\n)',
        content,
        re.IGNORECASE
    )

    if not section_match:
        print(f"  ❌ '{genre_name}' 장르 섹션을 찾을 수 없습니다.")
        return 0

    insert_pos = section_match.end()

    # ① 기존 refs 추출 (현재 섹션 내에서만, 블록 제거 전)
    existing_refs = _extract_existing_curated_refs(content, insert_pos)

    # ② 현재 섹션 범위 내 user_curated 블록만 제거
    sec_end = _section_end(content, insert_pos)
    existing_block = re.search(
        r'\n<!-- CURATED_REFS_START -->[\s\S]*?<!-- CURATED_REFS_END -->\n?',
        content[insert_pos:sec_end]
    )
    if existing_block:
        start = insert_pos + existing_block.start()
        end = insert_pos + existing_block.end()
        content = content[:start] + content[end:]
        sec_end = _section_end(content, insert_pos)  # 섹션 끝 위치 재계산

    # ③ 현재 섹션 내 기존 샘플 코드블록만 추출 후 ref #1로 편입, 제거
    base_ref = None
    code_block_m = re.search(r'```([\s\S]*?)```', content[insert_pos:sec_end])
    if code_block_m:
        base_content = code_block_m.group(1).strip()
        base_ref = {"source_url": "", "content": base_content}
        # 코드블록 제거
        cb_start = insert_pos + code_block_m.start()
        cb_end = insert_pos + code_block_m.end()
        content = content[:cb_start] + content[cb_end:]
        # insert_pos는 코드블록이 있던 자리 유지

    # ④ 새 songs를 ref 형식으로 변환
    new_refs = [{
        "source_url": s.get("source_url", "?"),
        "content": f"{s.get('styles', '')}\n\n{s.get('lyrics_structure', '')}",
    } for s in songs]

    # ⑤ 기본샘플 + 기존 큐레이션 + 신규 합산 후 한도 초과 시 Claude 판단으로 제거
    base_list = [base_ref] if base_ref else []
    all_refs = base_list + existing_refs + new_refs
    while len(all_refs) > MAX_CURATED_REFS:
        # 기본샘플(첫 번째)은 보호 — 1번 인덱스 이후에서만 제거
        candidates = all_refs[1:] if base_ref else all_refs
        remove_idx = _claude_pick_weakest_ref(genre_name, candidates)
        if base_ref:
            remove_idx += 1  # offset for protected base ref
        removed = all_refs.pop(remove_idx)
        print(f"  🗑 한도 초과({MAX_CURATED_REFS}개) 제거 → 레퍼런스 {remove_idx+1}: {removed['source_url']}")

    # ⑥ 레퍼런스 블록 재생성 (헤더 바로 아래에 삽입)
    blocks = [f"\n<!-- CURATED_REFS_START -->\n"]
    blocks.append(f"> 🎵 영구 레퍼런스 (user_curated) — 총 {len(all_refs)}곡 / 갱신일: {today}\n\n")

    for n, ref in enumerate(all_refs, 1):
        blocks.append(f"### 레퍼런스 {n}\n")
        if ref.get("source_url"):
            blocks.append(f"> 원본: {ref['source_url']}\n\n")
        blocks.append(f"```\n{ref['content']}\n```\n\n")
        saved_count += 1

    blocks.append("<!-- CURATED_REFS_END -->\n")

    curated_block = "".join(blocks)
    content = content[:insert_pos] + curated_block + content[insert_pos:]
    GENRE_SAMPLES_PATH.write_text(content, encoding="utf-8")

    return saved_count


def _clean_youtube_url(url: str) -> str:
    """YouTube URL에서 v 파라미터만 추출해 깨끗한 URL 반환. Gemini는 list/index 파라미터 처리 불가."""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    video_id = qs.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


def cmd_add_curated(genre_name: str, urls: list):
    """
    여러 개별 YouTube URL을 각각 분석해서 해당 장르의 영구 레퍼런스로 일괄 저장.
    각 URL을 단일 트랙으로 간주하고 analyze_video로 분석.
    """
    if genre_name not in EXISTING_GENRES:
        print(f"⚠ '{genre_name}'은 등록된 장르가 아닙니다.")
        print("  등록된 장르:")
        for g in EXISTING_GENRES:
            print(f"    - {g}")
        sys.exit(1)

    print(f"\n🎵 add-curated: {genre_name}")
    print(f"   총 {len(urls)}개 URL 분석 시작...\n")

    client = get_client()
    songs = []
    db = load_style_db()

    for i, url in enumerate(urls, 1):
        url = _clean_youtube_url(url)
        print(f"[{i}/{len(urls)}] {url}")
        result = analyze_video(url, client)

        if result is None:
            print(f"  ❌ 분석 실패, 건너뜀")
            if i < len(urls):
                time.sleep(2)
            continue

        if result.get("filter_out"):
            print(f"  ⛔ 제외: {result.get('filter_reason', '')}")
            if i < len(urls):
                time.sleep(2)
            continue

        track_num = len(songs) + 1
        songs.append({
            "track_number": track_num,
            "source_url": url,
            "styles": result.get("styles", ""),
            "lyrics_structure": result.get("lyrics_structure", ""),
            "vocal_gender": result.get("vocal_gender", "?"),
            "vocal_tone": result.get("vocal_tone", "?"),
            "bpm": result.get("bpm", "?"),
        })

        print(f"  ✓ {result.get('vocal_gender', '?')} / {result.get('vocal_tone', '?')}  {result.get('bpm', '?')}BPM")

        db["analyzed_count"] += 1
        if genre_name not in db["genres"]:
            db["genres"][genre_name] = {"name_ko": genre_name, "is_new": False, "samples": []}
        db["genres"][genre_name]["samples"].append({
            "source_url": url,
            "source": "user_curated",
            "track_number": track_num,
            "analyzed_at": result["analyzed_at"],
            "vocal_gender": result.get("vocal_gender"),
            "vocal_tone": result.get("vocal_tone"),
            "bpm": result.get("bpm"),
        })

        if i < len(urls):
            time.sleep(2)

    save_style_db(db)

    if not songs:
        print("\n❌ 저장할 유효한 곡이 없습니다.")
        return

    saved = save_curated_references_batch(genre_name, songs)
    print(f"\n✅ {saved}개 영구 레퍼런스 저장 완료")
    print(f"   파일: {GENRE_SAMPLES_PATH}")
    print(f"   태그: user_curated (주간 트렌드 교체로부터 보호됨)")


# ── analyze: 주간 트렌드 단일 영상 분석 ─────────────────
def analyze_video(url: str, client) -> dict | None:
    """Gemini API로 YouTube 영상 첫 번째 곡 분석 (트렌드용)."""
    prompt = ANALYSIS_PROMPT.format(
        filter_criteria=FILTER_CRITERIA,
        existing_genres="\n".join(f"- {g}" for g in EXISTING_GENRES),
        url=url
    )

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                {
                    "file_data": {
                        "file_uri": url,
                        "mime_type": "video/*"
                    }
                },
                prompt
            ]
        )
        raw = response.text.strip()

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            print(f"  ❌ JSON 파싱 실패: {raw[:200]}")
            return None

        result = json.loads(json_match.group())
        result["source_url"] = url
        result["analyzed_at"] = datetime.now().isoformat()
        return result

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Gemini API 오류: {e}")
        return None


def update_trend_reference(result: dict):
    """트렌드 분석 결과를 style-suggestions/에 저장 (검토 후 반영)."""
    genre_name = result.get("genre_name", "Unknown")
    is_new = result.get("is_new_genre", False)
    styles = result.get("styles", "")
    lyrics = result.get("lyrics_structure", "")

    if not GENRE_SAMPLES_PATH.exists():
        print(f"  ❌ 장르 샘플 파일 없음: {GENRE_SAMPLES_PATH}")
        return

    if is_new:
        current_content = GENRE_SAMPLES_PATH.read_text(encoding="utf-8")
        existing_sections = re.findall(r'^## (\d+)-(\d+)\.', current_content, re.MULTILINE)
        if existing_sections:
            last_main = max(int(m[0]) for m in existing_sections)
            last_sub = max(int(m[1]) for m in existing_sections if int(m[0]) == last_main)
            next_section = f"{last_main}-{last_sub + 1}"
        else:
            next_section = "4-8"

        genre_name_ko = result.get("genre_name_ko", genre_name)
        new_section = f"""
---

## {next_section}. {genre_name} ({genre_name_ko})

> 📡 Gemini 트렌드 분석 자동 추가 — {result['analyzed_at'][:10]}
> 원본 영상: {result['source_url']}

```
{styles}

{lyrics}
```
"""
        GENRE_SAMPLES_PATH.write_text(current_content + new_section, encoding="utf-8")
        print(f"  ✓ 신규 장르 추가: {next_section}. {genre_name}")
    else:
        suggestion_dir = AGENTS_DIR / "style-suggestions"
        suggestion_dir.mkdir(exist_ok=True)
        safe_name = re.sub(r'[^\w\-]', '_', genre_name)
        suggestion_path = suggestion_dir / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        suggestion_path.write_text(
            f"# {genre_name} 트렌드 업데이트 제안\n\n"
            f"> 원본 영상: {result['source_url']}\n"
            f"> 분석 일시: {result['analyzed_at']}\n\n"
            f"## 분석된 스타일\n\n```\n{styles}\n\n{lyrics}\n```\n",
            encoding="utf-8"
        )
        print(f"  📝 트렌드 제안 저장: style-suggestions/{suggestion_path.name}")


def cmd_analyze(urls: list[str]):
    """YouTube URL 목록 분석 → 주간 트렌드 교체형 레퍼런스 생성."""
    client = get_client()
    db = load_style_db()

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] 분석 중: {url}")
        result = analyze_video(url, client)
        if result is None:
            continue

        db["analyzed_count"] += 1

        if result.get("filter_out"):
            print(f"  ⛔ 제외: {result.get('filter_reason', '')}")
            db["filtered_out"].append({
                "url": url,
                "reason": result.get("filter_reason", ""),
                "analyzed_at": result["analyzed_at"]
            })
            continue

        genre = result["genre_name"]
        is_new = result.get("is_new_genre", False)
        print(f"  ✓ 장르: {genre} {'[신규]' if is_new else '[기존]'}")
        print(f"    보컬: {result.get('vocal_gender', '?')} / {result.get('vocal_tone', '?')}  BPM: {result.get('bpm', '?')}")

        if genre not in db["genres"]:
            db["genres"][genre] = {"name_ko": result.get("genre_name_ko", genre), "is_new": is_new, "samples": []}
            if is_new and genre not in db["new_genres"]:
                db["new_genres"].append(genre)

        db["genres"][genre]["samples"].append({
            "source_url": url,
            "source": "gemini_trend",
            "analyzed_at": result["analyzed_at"],
            "vocal_gender": result.get("vocal_gender"),
            "vocal_tone": result.get("vocal_tone"),
            "bpm": result.get("bpm"),
            "styles": result.get("styles"),
            "lyrics_structure": result.get("lyrics_structure"),
        })

        update_trend_reference(result)

        if i < len(urls):
            time.sleep(2)

    save_style_db(db)
    print(f"\n✅ 완료 ({db['analyzed_count']}개 누적 분석)")


def cmd_list_genres():
    db = load_style_db()
    print("── 기본 장르 ──")
    for g in EXISTING_GENRES:
        info = db.get("genres", {}).get(g, {})
        curated = sum(1 for s in info.get("samples", []) if s.get("source") == "user_curated")
        trend = sum(1 for s in info.get("samples", []) if s.get("source") == "gemini_trend")
        status = f"영구 {curated}개 / 트렌드 {trend}개" if curated or trend else "미분석"
        print(f"  - {g}  [{status}]")

    if db.get("new_genres"):
        print("\n── Gemini 분석으로 추가된 신규 장르 ──")
        for g in db["new_genres"]:
            info = db["genres"].get(g, {})
            print(f"  - {g} ({info.get('name_ko', '')})  샘플 {len(info.get('samples', []))}개")

    print(f"\n총 분석: {db.get('analyzed_count', 0)}개  |  마지막 업데이트: {db.get('last_updated', '없음')}")


def cmd_update_db():
    db = load_style_db()
    print(f"분석 영상: {db.get('analyzed_count', 0)}개")
    print(f"등록 장르: {len(db.get('genres', {}))}개")
    save_style_db(db)
    print("✅ style-database.json 저장됨")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "setup-genre":
        if len(sys.argv) < 4:
            print("❌ 사용법: setup-genre <장르명> <youtube_url>")
            print('   예시: python3 scripts/gemini_analyzer.py setup-genre "Lo-fi Focus & Cafe Chill" https://youtu.be/...')
            sys.exit(1)
        cmd_setup_genre(sys.argv[2], sys.argv[3])

    elif cmd == "add-curated":
        if len(sys.argv) < 4:
            print("❌ 사용법: add-curated <장르명> <url1> [<url2> ...]")
            print('   예시: python3 scripts/gemini_analyzer.py add-curated "Groove Hip-hop & Chill Pop" https://youtu.be/... https://youtu.be/...')
            sys.exit(1)
        cmd_add_curated(sys.argv[2], sys.argv[3:])

    elif cmd == "analyze":
        if len(sys.argv) < 3:
            print("❌ URL을 하나 이상 입력해주세요.")
            sys.exit(1)
        cmd_analyze(sys.argv[2:])

    elif cmd == "list-genres":
        cmd_list_genres()

    elif cmd == "update-db":
        cmd_update_db()

    else:
        print(f"❌ 알 수 없는 명령: {cmd}")
        print(__doc__)
        sys.exit(1)
