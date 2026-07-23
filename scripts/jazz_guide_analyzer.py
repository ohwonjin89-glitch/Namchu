#!/usr/bin/env python3
"""
Jazz Instrumental 프롬프트 가이드 생성기.
Gemini API로 20개 YouTube 링크를 직접 청취 분석 후
Suno 프롬프트 가이드(DEFAULT_GUIDE 형식) 출력.

Usage:
  python3 scripts/jazz_guide_analyzer.py <url1> <url2> ... <url20>
"""

import json
import os
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from google import genai
except ImportError:
    print("❌ google-genai 패키지 없음. 설치: pip install google-genai")
    sys.exit(1)

ANALYSIS_PROMPT = """
이 YouTube 영상의 음악을 직접 듣고 분석해줘. 이 곡은 재즈 인스트루멘탈이야 (가사 없음).
JSON 외의 다른 텍스트 없이 JSON만 출력해.

분석 대상:
1. 메인 재즈 서브장르 (bebop, cool jazz, bossa nova, smooth jazz, jazz-funk, latin jazz, modal jazz 등)
2. 주요 악기 (piano, upright bass, electric bass, acoustic guitar, vibraphone, trumpet, saxophone, flute 등)
3. 드럼 패턴 (brushed drums, swing drums, bossa rhythm, samba groove 등)
4. BPM 추정값 (숫자)
5. 음악 무드 (영어 형용사/명사 3~5개)
6. 분위기 설명 (카페/바/심야 등 한국어 1~2개)
7. Suno AI에 적합한 style 태그 (영어 콤마 구분 5~10개)

출력 JSON:
{
  "subgenre": "메인 서브장르 영어",
  "instruments": ["악기1", "악기2", ...],
  "drum_pattern": "드럼 패턴 설명 영어",
  "bpm": 95,
  "mood_keywords": ["keyword1", "keyword2", ...],
  "atmosphere_ko": ["분위기1", "분위기2"],
  "suno_tags": "tag1, tag2, tag3, ...",
  "one_line_style": "완성된 영어 문장 스타일 설명 (장르, 악기, 무드, BPM 포함)"
}
"""

def clean_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    video_id = qs.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def analyze_one(url: str, client) -> dict | None:
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                {"file_data": {"file_uri": url, "mime_type": "video/*"}},
                ANALYSIS_PROMPT
            ]
        )
        raw = response.text.strip()
        m = re.search(r'\{[\s\S]*\}', raw)
        if not m:
            print(f"  ❌ JSON 없음: {raw[:200]}")
            return None
        return json.loads(m.group())
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return None

def aggregate_results(results: list[dict]) -> str:
    """분석 결과를 집계해서 DEFAULT_GUIDE 형식의 가이드 텍스트 생성."""
    from collections import Counter

    subgenres = Counter()
    instruments = Counter()
    drum_patterns = Counter()
    bpms = []
    moods = Counter()
    atmospheres = Counter()
    all_suno_tags = Counter()
    style_lines = []

    for r in results:
        if not r:
            continue
        subgenres[r.get("subgenre", "")] += 1
        for inst in r.get("instruments", []):
            instruments[inst.lower()] += 1
        dp = r.get("drum_pattern", "")
        if dp:
            drum_patterns[dp] += 1
        bpm = r.get("bpm")
        if bpm and isinstance(bpm, (int, float)):
            bpms.append(int(bpm))
        for kw in r.get("mood_keywords", []):
            moods[kw.lower()] += 1
        for atm in r.get("atmosphere_ko", []):
            atmospheres[atm] += 1
        for tag in r.get("suno_tags", "").split(","):
            t = tag.strip().lower()
            if t:
                all_suno_tags[t] += 1
        sl = r.get("one_line_style", "")
        if sl:
            style_lines.append(sl)

    bpm_min = min(bpms) if bpms else 80
    bpm_max = max(bpms) if bpms else 140
    bpm_avg = int(sum(bpms) / len(bpms)) if bpms else 110

    top_subgenres = [g for g, _ in subgenres.most_common(3) if g]
    top_instruments = [i for i, _ in instruments.most_common(8) if i]
    top_drums = [d for d, _ in drum_patterns.most_common(3) if d]
    top_moods = [m for m, _ in moods.most_common(6) if m]
    top_atm = [a for a, _ in atmospheres.most_common(4) if a]
    top_tags = [t for t, _ in all_suno_tags.most_common(12) if t]

    # 악기 카테고리별 분류
    piano_types = [i for i in top_instruments if any(x in i for x in ["piano", "rhodes", "organ", "keys", "keyboard", "vibraphone", "marimba"])]
    guitar_types = [i for i in top_instruments if any(x in i for x in ["guitar"])]
    bass_types = [i for i in top_instruments if any(x in i for x in ["bass"])]
    wind_types = [i for i in top_instruments if any(x in i for x in ["trumpet", "saxophone", "sax", "flute", "clarinet", "trombone"])]
    other_types = [i for i in top_instruments if i not in piano_types + guitar_types + bass_types + wind_types]

    # 네거티브 태그 (인스트루멘탈이므로 보컬 관련 모두 제외)
    neg_tags = "vocals, singing, lyrics, humming, ooh-ooh, la-la, mm-mm, whoa-oh, rap, spoken word, EDM drop, trap, heavy metal, kpop"

    lines = []
    lines.append("━━ Jazz Instrumental 가이드 ━━")
    lines.append("")
    lines.append("[장르 베이스]")
    if top_subgenres:
        lines.append("- 서브장르: " + " / ".join(top_subgenres))
    lines.append("- 핵심: instrumental only, no vocals, no lyrics")
    lines.append("")
    lines.append("[템포 & 리듬]")
    lines.append(f"- BPM: {bpm_min}~{bpm_max} BPM (평균 {bpm_avg}BPM)")
    if top_drums:
        lines.append("- 드럼 패턴: " + " / ".join(top_drums[:2]))
    lines.append("")
    lines.append("[악기 구성]")
    if piano_types:
        lines.append("- 건반: " + " / ".join(piano_types[:2]))
    if guitar_types:
        lines.append("- 기타: " + " / ".join(guitar_types[:2]))
    if bass_types:
        lines.append("- 베이스: " + " / ".join(bass_types[:2]))
    if wind_types:
        lines.append("- 관악기: " + " / ".join(wind_types[:3]))
    if other_types:
        lines.append("- 기타: " + " / ".join(other_types[:3]))
    lines.append("")
    lines.append("[무드 & 분위기]")
    if top_moods:
        lines.append("- 무드: " + " / ".join(top_moods[:5]))
    if top_atm:
        lines.append("- 분위기: " + " · ".join(top_atm))
    lines.append("")
    lines.append("[Suno 권장 태그]")
    if top_tags:
        lines.append("- " + ", ".join(top_tags))
    lines.append("")
    lines.append("[네거티브 태그]")
    lines.append("- " + neg_tags)
    lines.append("")
    lines.append("[레퍼런스 스타일 예시]")
    for i, sl in enumerate(style_lines[:3], 1):
        lines.append(f"  {i}. {sl}")

    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # --merge 플래그: 기존 jazz_guide_raw.json에 결과 추가
    merge_mode = "--merge" in sys.argv
    raw_urls = [a for a in sys.argv[1:] if not a.startswith("--")]
    urls = [clean_url(u) for u in raw_urls]
    print(f"🎷 Jazz Instrumental 분석 시작 — {len(urls)}개 영상\n")

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        r = analyze_one(url, client)
        if r:
            results.append(r)
            subgenre = r.get("subgenre", "?")
            bpm = r.get("bpm", "?")
            moods = ", ".join(r.get("mood_keywords", [])[:3])
            print(f"  ✓ {subgenre}  {bpm}BPM  [{moods}]")
        else:
            print(f"  ⚠ 분석 실패, 건너뜀")
        if i < len(urls):
            time.sleep(3)

    if not results:
        print("\n❌ 분석된 곡이 없습니다.")
        sys.exit(1)

    print(f"\n✅ {len(results)}/{len(urls)}곡 분석 완료\n")
    print("=" * 60)
    guide = aggregate_results(results)
    print(guide)
    print("=" * 60)

    # JSON 원시 데이터도 저장 (merge 모드면 기존 결과에 추가)
    import pathlib
    out_path = pathlib.Path(__file__).parent.parent / ".claude" / "agents" / "jazz_guide_raw.json"
    if merge_mode and out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            results = existing + results
            print(f"  (기존 {len(existing)}개 + 신규 {len(results)-len(existing)}개 = {len(results)}개 합산)")
        except Exception:
            pass
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 원시 데이터 저장: {out_path}")
    print("\n📋 위 가이드를 복사해서 대시보드에 새 가이드로 추가하세요.")

    # guide.txt로도 저장
    guide_path = pathlib.Path(__file__).parent.parent / ".claude" / "agents" / "jazz_guide.txt"
    guide_path.write_text(guide, encoding="utf-8")
    print(f"📄 가이드 텍스트 저장: {guide_path}")

if __name__ == "__main__":
    main()
