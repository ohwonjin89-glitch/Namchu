#!/usr/bin/env python3
"""
기존 음악 파일부터 이미지→영상→YouTube 업로드까지 재개합니다.
사용법:
  python resume_from_music.py DGM 20260612_182647
"""
import os
import sys
import json
import datetime

# ── 환경 설정 ──────────────────────────────────────────────────────────────
for _p in ["/mnt/c/suno-api/.env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
    if os.path.exists(_p):
        with open(_p, encoding="utf-8", errors="ignore") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
        break

os.environ.setdefault("SUNO_API_BASE", "http://172.28.32.1:3000")

sys.path.insert(0, os.path.dirname(__file__))
from core.agent import Agent, agent_dialogue
from core.tools import generate_image, _fallback_image, create_video, upload_youtube, _to_win
from core.logger import MeetingLogger
from core.pipeline import load_instructions, parse_upload_info


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "DGM"
    date_str = sys.argv[2] if len(sys.argv) > 2 else None

    if not date_str:
        # Find latest folder
        base = os.path.join(os.environ.get("DGM_OUTPUT_BASE", "/mnt/c/Users/오원진/AppData/Local/dgm_output"), channel)
        folders = sorted([f for f in os.listdir(base) if os.path.isdir(os.path.join(base, f))])
        if not folders:
            print("출력 폴더를 찾을 수 없습니다.")
            sys.exit(1)
        date_str = folders[-1]
        print(f"가장 최근 폴더 사용: {date_str}")

    output_dir = os.path.join(os.environ.get("DGM_OUTPUT_BASE", "/mnt/c/Users/오원진/AppData/Local/dgm_output"), channel, date_str)
    music_path = os.path.join(output_dir, "music.mp3")

    if not os.path.exists(music_path):
        print(f"음악 파일이 없습니다: {music_path}")
        sys.exit(1)

    print(f"\n{'='*52}")
    print(f"  재개: {channel} / {date_str}")
    print(f"  음악: {music_path}")
    print(f"{'='*52}\n")

    logger = MeetingLogger(output_dir, channel, date_str)
    meeting_log: list = []

    # Concept placeholder
    concept = {
        "title": "감성 플레이리스트",
        "style": "Korean chill pop, emotional",
        "mood": "감성적, 따뜻함",
    }

    # Load state if exists
    state_path = f"/tmp/dgm_state_{channel}.json"
    state = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
        concept = state.get("selectedPrompt", concept)
        print(f"  상태 로드: {state.get('steps', {})}")

    top_titles = state.get("topTitles", [])

    # ── 이미지 컨셉 회의 ──────────────────────────────────────────────────
    print("\n[4/6] 이미지 컨셉 회의 (디렉터 ↔ 이미지 디자이너)...")
    director = Agent("디렉터", load_instructions("director"))
    image_designer = Agent("이미지_디자이너", load_instructions("image_designer"))
    quality_checker = Agent("품질_검수자", load_instructions("quality_checker"))

    image_brief = (
        f"음악 제목: {concept.get('title', '감성 플레이리스트')}\n"
        f"스타일: {concept.get('style', 'Korean chill pop')}\n"
        f"분위기: {concept.get('mood', '감성적, 차분한')}\n\n"
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
        image_path = generate_image(image_prompt, output_dir)
        state["bgImagePath"] = image_path
        state["steps"] = state.get("steps", {})
        state["steps"]["image"] = "done"
        print(f"  이미지 완료: {image_path}")
    except Exception as e:
        print(f"  이미지 API 실패: {e} — 기본 배경 생성")
        image_path = _fallback_image(output_dir)
        state["bgImagePath"] = image_path
        state.setdefault("steps", {})["image"] = "done"

    # ── 영상 합성 ──────────────────────────────────────────────────────────
    print("\n[5/6] 영상 합성 중...")
    print(f"  음악: {music_path} → Windows: {_to_win(music_path)}")
    print(f"  이미지: {image_path} → Windows: {_to_win(image_path)}")
    video_path = create_video(music_path, image_path, output_dir, title=concept["title"])
    state["videoPath"] = video_path
    state.setdefault("steps", {})["video"] = "done"
    print(f"  영상 완료: {video_path}")

    # ── 품질 검수 ─────────────────────────────────────────────────────────
    qa_prompt = (
        f"완성된 프로젝트를 검토하고 업로드 정보를 생성해주세요:\n\n"
        f"- 채널: {channel}\n"
        f"- 음악 제목: {concept.get('title', '')}\n"
        f"- 스타일: {concept.get('style', '')}\n\n"
        "아래 형식으로 정확히 답하세요:\n"
        "TITLE: (YouTube 업로드 제목, 50자 이내)\n"
        "DESCRIPTION: (설명문, 200자 이내, 해시태그 포함)"
    )
    qa_result = quality_checker.chat(qa_prompt)
    logger.log("품질_검수자", qa_prompt, qa_result, 0)
    upload_info = parse_upload_info(qa_result, concept, top_titles)
    state["uploadTitle"] = upload_info["title"]

    # ── YouTube 업로드 ─────────────────────────────────────────────────────
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
            state.setdefault("steps", {})["upload"] = "done"
            state["status"] = "completed"
            print(f"  ✅ 업로드 완료: {yt_url}")
        else:
            raise RuntimeError(str(result))
    except Exception as e:
        state.setdefault("steps", {})["upload"] = "error"
        state["uploadError"] = str(e)
        state["status"] = "upload_failed"
        print(f"  ❌ 업로드 실패: {e}")

    # ── 저장 ──────────────────────────────────────────────────────────────
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    logger.save(state)

    sep = "=" * 52
    print(f"\n{sep}")
    print("🎉 재개 완료!")
    print(f"  채널  : {channel}")
    print(f"  제목  : {upload_info['title']}")
    if state.get("uploadedUrl"):
        print(f"  URL   : {state['uploadedUrl']}")
    print(f"  폴더  : {output_dir}")
    print(f"  회의록: {output_dir}/meeting_log.md")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
