"""Main pipeline — runs all agents in sequence with dialogue."""
import os
import json
import re
import datetime
import random
from pathlib import Path

from .agent import Agent, agent_dialogue
from .tools import (
    get_trend_data, generate_music, generate_image,
    create_video, upload_youtube
)
from .logger import MeetingLogger

INSTRUCTIONS_DIR = Path(__file__).parent.parent / "instructions"


def load_instructions(name: str) -> str:
    path = INSTRUCTIONS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"당신은 {name} 에이전트입니다. 최선을 다해 역할을 수행하세요."


def parse_music_concept(text: str) -> dict:
    """Extract structured concept from agent reply."""
    concept = {}
    patterns = {
        "title": r"제목\s*[:：]\s*(.+)",
        "style": r"(?:음악\s*)?스타일\s*[:：]\s*(.+)",
        "guide": r"(?:가사|가이드)\s*[:：]\s*(.+)",
        "mood": r"분위기\s*(?:키워드)?\s*[:：]\s*(.+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            concept[key] = m.group(1).strip()

    if not concept.get("title"):
        # Fallback: first non-empty line
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and len(line) < 60:
                concept["title"] = line
                break

    concept.setdefault("title", "감성 플레이리스트")
    concept.setdefault("style", "Korean chill pop, emotional, relaxing")
    concept.setdefault("guide", "Peaceful melody, soft piano, ambient")
    concept.setdefault("instrumental", True)
    return concept


def parse_upload_info(text: str, concept: dict, top_titles: list) -> dict:
    title_m = re.search(r"TITLE\s*[:：]\s*(.+)", text, re.IGNORECASE)
    desc_m = re.search(r"DESCRIPTION\s*[:：]\s*([\s\S]+?)(?:\n\n|\Z)", text, re.IGNORECASE)

    title = title_m.group(1).strip() if title_m else None
    description = desc_m.group(1).strip() if desc_m else None

    # Fallback title formats
    if not title:
        base = concept.get("title", "감성 플레이리스트")
        formats = [
            f"Playlist | {base}",
            f"{base} | 감성 플레이리스트 🎵",
            f"🎧 {base} playlist",
            f"[Playlist] {base}",
            f"{base} | Korean Playlist",
            f"감성 플레이리스트 | {base} 🎶",
            f"{base} | 틀어두기 좋은 음악 모음",
        ]
        title = random.choice(formats)

    if not description:
        related = "\n".join([f"· {t}" for t in top_titles[:3]])
        description = (
            f"감성적인 음악 모음 🎵\n\n{related}\n\n"
            "📌 구독하고 매주 새로운 플레이리스트를 받아보세요\n"
            "🔔 알림 설정 ON\n\n"
            "#플레이리스트 #감성음악 #KoreanPlaylist #ChillMusic #음악모음"
        )

    return {"title": title, "description": description}


def run_pipeline(channel: str = "DGM") -> dict:
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_linux = f"/mnt/c/Users/오원진/AppData/Local/dgm_output/{channel}/{date_str}"
    os.makedirs(output_dir_linux, exist_ok=True)

    logger = MeetingLogger(output_dir_linux, channel, date_str)
    meeting_log: list = []

    state = {
        "channel": channel,
        "date": date_str,
        "outputDirLinux": output_dir_linux,
        "steps": {s: "pending" for s in
                  ["trend", "prompt", "music", "image", "video", "upload"]}
    }

    sep = "=" * 52
    print(f"\n{sep}")
    print(f"  DGM 파이프라인 시작: {channel}")
    print(f"  {date_str}")
    print(f"{sep}\n")

    # ── 에이전트 초기화 ────────────────────────────────────────────────
    director = Agent("디렉터", load_instructions("director"))
    prompt_writer = Agent("프롬프트_작성자", load_instructions("prompt_writer"))
    image_designer = Agent("이미지_디자이너", load_instructions("image_designer"))
    quality_checker = Agent("품질_검수자", load_instructions("quality_checker"))

    # ── Step 1: 트렌드 분석 ────────────────────────────────────────────
    print("[1/6] 트렌드 분석...")
    trend_data = get_trend_data()
    trend_videos = trend_data.get("trendVideos", [])[:5]
    top_titles = [v.get("title", "") for v in trend_videos]
    state["trendVideos"] = trend_videos
    state["topTitles"] = top_titles
    state["steps"]["trend"] = "done"
    print(f"  {len(top_titles)}개 트렌드 수집 완료")

    # ── Step 2: 프롬프트 회의 ──────────────────────────────────────────
    print("\n[2/6] 음악 컨셉 회의 (디렉터 ↔ 프롬프트 작성자)...")
    trend_summary = "\n".join([f"- {t}" for t in top_titles]) or "- 감성적인 한국 플레이리스트"

    initial_brief = (
        f"채널: {channel}\n"
        f"현재 유행하는 YouTube 플레이리스트 제목들:\n{trend_summary}\n\n"
        "이 트렌드를 분석해서 다음 영상에 적합한 음악 컨셉을 제안해주세요.\n"
        "아래 형식을 정확히 사용하세요:\n"
        "- 제목: (한국어, 30자 이내)\n"
        "- 음악 스타일: (장르와 분위기, 영문)\n"
        "- 가이드: (영문 키워드, 50자 이내)\n"
        "- 분위기 키워드: (3개, 쉼표 구분)"
    )

    music_concept_text = agent_dialogue(
        director, prompt_writer, initial_brief, max_rounds=3, meeting_log=meeting_log
    )

    for entry in meeting_log:
        logger.log(entry["speaker"], "", entry["content"], entry["round"])
    meeting_log.clear()

    concept = parse_music_concept(music_concept_text)
    state["selectedPrompt"] = concept
    state["steps"]["prompt"] = "done"
    print(f"  컨셉 확정: {concept['title']}")

    # ── Step 3: 음악 생성 ──────────────────────────────────────────────
    print(f"\n[3/6] 음악 생성 중... ({concept['title']})")
    music_result = generate_music(concept, output_dir_linux)
    state["musicFile"] = music_result["path"]
    state["musicIds"] = music_result["ids"]
    state["steps"]["music"] = "done"
    print(f"  음악 완료: {music_result['path']}")

    # ── Step 4: 이미지 컨셉 회의 ──────────────────────────────────────
    print("\n[4/6] 이미지 컨셉 회의 (디렉터 ↔ 이미지 디자이너)...")
    image_brief = (
        f"음악 제목: {concept.get('title', '')}\n"
        f"스타일: {concept.get('style', '')}\n"
        f"분위기: {concept.get('mood', '')}\n\n"
        "이 음악에 어울리는 YouTube 배경/썸네일 이미지 생성 프롬프트를 작성해주세요.\n"
        "영문 이미지 생성 프롬프트 형식으로 60-100 단어로 작성하세요.\n"
        "cinematic, high quality, 16:9 ratio 포함 필수."
    )

    image_prompt = agent_dialogue(
        director, image_designer, image_brief, max_rounds=3, meeting_log=meeting_log
    )

    for entry in meeting_log:
        logger.log(entry["speaker"], "", entry["content"], entry["round"])
    meeting_log.clear()

    state["imagePrompt"] = image_prompt

    print("  이미지 생성 중...")
    try:
        image_path = generate_image(image_prompt, output_dir_linux)
        state["bgImagePath"] = image_path
        state["steps"]["image"] = "done"
        print(f"  이미지 완료: {image_path}")
    except Exception as e:
        print(f"  이미지 API 실패: {e} — 기본 배경 생성")
        from .tools import _fallback_image
        image_path = _fallback_image(output_dir_linux)
        state["bgImagePath"] = image_path
        state["steps"]["image"] = "done"

    # ── Step 5: 영상 제작 ──────────────────────────────────────────────
    print("\n[5/6] 영상 합성 중...")
    video_path = create_video(
        music_result["path"], image_path,
        output_dir_linux, title=concept["title"]
    )
    state["videoPath"] = video_path
    state["steps"]["video"] = "done"
    print(f"  영상 완료: {video_path}")

    # ── 품질 검수 ─────────────────────────────────────────────────────
    qa_prompt = (
        f"완성된 프로젝트를 검토하고 업로드 정보를 생성해주세요:\n\n"
        f"- 채널: {channel}\n"
        f"- 음악 제목: {concept.get('title', '')}\n"
        f"- 스타일: {concept.get('style', '')}\n"
        f"- 이미지 컨셉: {image_prompt[:120]}...\n\n"
        "아래 형식으로 정확히 답하세요:\n"
        "TITLE: (YouTube 업로드 제목, 50자 이내)\n"
        "DESCRIPTION: (설명문, 200자 이내, 해시태그 포함)"
    )
    qa_result = quality_checker.chat(qa_prompt)
    logger.log("품질_검수자", qa_prompt, qa_result, 0)

    upload_info = parse_upload_info(qa_result, concept, top_titles)
    state["uploadTitle"] = upload_info["title"]

    # ── Step 6: YouTube 업로드 ─────────────────────────────────────────
    print(f"\n[6/6] YouTube 업로드 중...")
    print(f"  제목: {upload_info['title']}")
    try:
        result = upload_youtube(
            video_path,
            upload_info["title"],
            upload_info["description"],
            ["플레이리스트", "감성음악", "KoreanPlaylist", "chill", "음악모음"]
        )
        if result.get("success"):
            yt_url = f"https://www.youtube.com/watch?v={result['videoId']}"
            state["uploadedUrl"] = yt_url
            state["uploadedVideoId"] = result["videoId"]
            state["steps"]["upload"] = "done"
            state["status"] = "completed"
            print(f"  ✅ 업로드 완료: {yt_url}")
        else:
            raise RuntimeError(str(result))
    except Exception as e:
        state["steps"]["upload"] = "error"
        state["uploadError"] = str(e)
        state["status"] = "upload_failed"
        print(f"  ❌ 업로드 실패: {e}")

    # ── 상태 저장 ─────────────────────────────────────────────────────
    state_path = f"/tmp/dgm_state_{channel}.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    logger.save(state)

    # ── 최종 리포트 ───────────────────────────────────────────────────
    print(f"\n{sep}")
    print("🎉 파이프라인 완료!")
    print(f"  채널  : {channel}")
    print(f"  제목  : {upload_info['title']}")
    if state.get("uploadedUrl"):
        print(f"  URL   : {state['uploadedUrl']}")
    print(f"  폴더  : {output_dir_linux}")
    print(f"  회의록: {output_dir_linux}/meeting_log.md")
    print(f"{sep}\n")

    return state
