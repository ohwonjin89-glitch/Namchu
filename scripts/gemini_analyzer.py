#!/usr/bin/env python3
"""
Gemini API로 YouTube 영상을 분석하여 DGM 프롬프트 가이드를 생성합니다.

Usage:
  python3 scripts/gemini_analyzer.py analyze <youtube_url> [<youtube_url> ...]
  python3 scripts/gemini_analyzer.py update-db          # style-database.json 갱신
  python3 scripts/gemini_analyzer.py list-genres        # 현재 등록된 장르 목록

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

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai 패키지 없음. 설치: pip install google-generativeai")
    sys.exit(1)

# ── 경로 설정 ────────────────────────────────────────────
PROJECT_DIR = Path("/workspace/suno-api") if Path("/workspace/suno-api").exists() else Path("/mnt/c/suno-api")
AGENTS_DIR = PROJECT_DIR / ".claude" / "agents"
GENRE_SAMPLES_PATH = AGENTS_DIR / "music-generator-genre-samples.md"
STYLE_DB_PATH = AGENTS_DIR / "style-database.json"
BACKUP_DIR = AGENTS_DIR / "backups"

# ── 기존 장르 목록 (music-generator-genre-samples.md 기반) ───
EXISTING_GENRES = [
    "Lo-fi Focus & Cafe Chill",
    "Groove Hip-hop & Chill Pop",
    "Late Night R&B & Soul",
    "Upbeat City Pop & Funk Groove",
    "Acoustic Indie Pop & Folk Soul",
    "Chillwave & Synth Pop",
    "Jazz-hop & Bossa Nova Chill",
]

# ── 우리 채널 성격과 맞지 않아 제외할 기준 ──────────────────
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

# ── Gemini에게 보낼 분석 프롬프트 ───────────────────────────
ANALYSIS_PROMPT = """
이 YouTube 영상의 음악을 분석해서 아래 JSON 형식 그대로 출력해줘.
JSON 외의 다른 텍스트 없이 JSON만 출력해.

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
  "styles": "1) Styles\\n[반드시 포함: 장르명, 주요 악기 나열, 보컬 성별(female/male/none), 보컬 톤(husky/airy/warm/bright 등), BPM 숫자, 전반적 분위기, 믹스 특성. 참고 예시: 'Lo-fi hip-hop with chill boom bap. A soft female vocal leads with an airy breathy tone. The tempo is 84 BPM...']",
  "lyrics_structure": "2) Lyrics\\n[Hook]\\n[가사 예시]\\n\\n[Verse 1]\\n[악기/분위기 지시어]\\n[가사 예시]\\n\\n[Pre-Chorus]\\n[지시어]\\n[가사]\\n\\n[Chorus]\\n[지시어]\\n[가사]\\n\\n[Verse 2]\\n[지시어]\\n[가사]\\n\\n[Bridge]\\n[지시어]\\n[가사]\\n\\n[Outro]\\n[지시어]\\n[가사]",
  "vocal_gender": "female",
  "vocal_tone": "보컬 톤 한 단어 (한국어: 허스키/맑은/따뜻한/몽환적/청량한 등)",
  "bpm": 80,
  "image_keywords": "Midjourney 영어 프롬프트 (20단어 이내, 배경 이미지용)",
  "image_palette": "색상 팔레트 설명 (한국어, 2~3가지 색)",
  "image_style": "이미지 분위기 1문장 (한국어)"
}}

YouTube URL: {url}
"""


def load_style_db() -> dict:
    """style-database.json 로드 (없으면 초기화)."""
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
    """style-database.json 저장."""
    db["last_updated"] = datetime.now().isoformat()
    STYLE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STYLE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def analyze_video(url: str, model) -> dict | None:
    """Gemini API로 YouTube 영상 분석."""
    prompt = ANALYSIS_PROMPT.format(
        filter_criteria=FILTER_CRITERIA,
        existing_genres="\n".join(f"- {g}" for g in EXISTING_GENRES),
        url=url
    )

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # JSON 블록 추출
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


def update_genre_samples(result: dict):
    """
    분석 결과를 music-generator-genre-samples.md에 새 장르로 추가.
    기존 장르면 해당 섹션을 업데이트하고, 신규 장르면 새 섹션 추가.
    """
    genre_name = result.get("genre_name", "Unknown")
    genre_name_ko = result.get("genre_name_ko", genre_name)
    is_new = result.get("is_new_genre", False)
    styles = result.get("styles", "")
    lyrics = result.get("lyrics_structure", "")

    if not GENRE_SAMPLES_PATH.exists():
        print(f"  ❌ 장르 샘플 파일 없음: {GENRE_SAMPLES_PATH}")
        return

    current_content = GENRE_SAMPLES_PATH.read_text(encoding="utf-8")

    if is_new:
        # 신규 장르 섹션 추가
        # 현재 마지막 섹션 번호 파악
        existing_sections = re.findall(r'^## (\d+)-(\d+)\.', current_content, re.MULTILINE)
        if existing_sections:
            last_main = max(int(m[0]) for m in existing_sections)
            last_sub = max(int(m[1]) for m in existing_sections if int(m[0]) == last_main)
            next_section = f"{last_main}-{last_sub + 1}"
        else:
            next_section = "4-8"

        new_section = f"""
---

## {next_section}. {genre_name} ({genre_name_ko})

> 📡 Gemini 분석 자동 추가 — {result['analyzed_at'][:10]}
> 원본 영상: {result['source_url']}

```
{styles}

{lyrics}
```
"""
        updated_content = current_content + new_section
        GENRE_SAMPLES_PATH.write_text(updated_content, encoding="utf-8")
        print(f"  ✓ 신규 장르 추가: {next_section}. {genre_name}")

    else:
        # 기존 장르 — style-database에만 기록 (md 파일 덮어쓰지 않음)
        # 사용자가 직접 검토 후 반영하도록 별도 파일에 제안 저장
        suggestion_dir = AGENTS_DIR / "style-suggestions"
        suggestion_dir.mkdir(exist_ok=True)
        safe_name = re.sub(r'[^\w\-]', '_', genre_name)
        suggestion_path = suggestion_dir / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        suggestion_path.write_text(
            f"# {genre_name} 스타일 업데이트 제안\n\n"
            f"> 원본 영상: {result['source_url']}\n"
            f"> 분석 일시: {result['analyzed_at']}\n\n"
            f"## 분석된 스타일\n\n```\n{styles}\n\n{lyrics}\n```\n",
            encoding="utf-8"
        )
        print(f"  📝 기존 장르 업데이트 제안 저장: style-suggestions/{suggestion_path.name}")
        print(f"     직접 검토 후 music-generator-genre-samples.md에 반영하세요.")


def cmd_analyze(urls: list[str]):
    """YouTube URL 목록을 분석하고 결과를 style-database에 저장."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        print("   export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    db = load_style_db()

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] 분석 중: {url}")

        result = analyze_video(url, model)
        if result is None:
            continue

        db["analyzed_count"] += 1

        if result.get("filter_out"):
            reason = result.get("filter_reason", "")
            print(f"  ⛔ 제외: {reason}")
            db["filtered_out"].append({
                "url": url,
                "reason": reason,
                "analyzed_at": result["analyzed_at"]
            })
            continue

        genre = result["genre_name"]
        is_new = result.get("is_new_genre", False)

        print(f"  ✓ 장르: {genre} {'[신규]' if is_new else '[기존]'}")
        print(f"    보컬: {result.get('vocal_gender', '?')} / {result.get('vocal_tone', '?')}")
        print(f"    BPM: {result.get('bpm', '?')}")

        # style-database 업데이트
        if genre not in db["genres"]:
            db["genres"][genre] = {
                "name_ko": result.get("genre_name_ko", genre),
                "is_new": is_new,
                "samples": []
            }
            if is_new and genre not in db["new_genres"]:
                db["new_genres"].append(genre)

        db["genres"][genre]["samples"].append({
            "source_url": url,
            "analyzed_at": result["analyzed_at"],
            "vocal_gender": result.get("vocal_gender"),
            "vocal_tone": result.get("vocal_tone"),
            "bpm": result.get("bpm"),
            "styles": result.get("styles"),
            "lyrics_structure": result.get("lyrics_structure"),
            "image_keywords": result.get("image_keywords"),
            "image_palette": result.get("image_palette"),
            "image_style": result.get("image_style")
        })

        # 장르 샘플 파일 업데이트
        update_genre_samples(result)

        # API 호출 간 딜레이 (Rate Limit 방지)
        if i < len(urls):
            time.sleep(2)

    save_style_db(db)
    print(f"\n✅ style-database.json 업데이트 완료 ({db['analyzed_count']}개 누적 분석)")


def cmd_list_genres():
    """현재 등록된 장르 목록 출력."""
    db = load_style_db()
    print("── 기본 장르 (music-generator-genre-samples.md) ──")
    for g in EXISTING_GENRES:
        print(f"  - {g}")

    if db.get("new_genres"):
        print("\n── Gemini 분석으로 추가된 신규 장르 ──")
        for g in db["new_genres"]:
            info = db["genres"].get(g, {})
            count = len(info.get("samples", []))
            print(f"  - {g} ({info.get('name_ko', '')})  샘플 {count}개")

    print(f"\n총 분석 영상: {db.get('analyzed_count', 0)}개")
    print(f"제외된 영상: {len(db.get('filtered_out', []))}개")
    print(f"마지막 업데이트: {db.get('last_updated', '없음')}")


def cmd_update_db():
    """기존 style-database 통계 출력 및 정리."""
    db = load_style_db()
    print(f"분석 영상: {db.get('analyzed_count', 0)}개")
    print(f"등록 장르: {len(db.get('genres', {}))}개")
    print(f"신규 장르: {len(db.get('new_genres', []))}개")
    save_style_db(db)
    print("✅ style-database.json 저장됨")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "analyze":
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
