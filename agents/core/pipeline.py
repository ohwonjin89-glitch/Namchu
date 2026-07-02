"""Main pipeline — runs all agents in sequence with dialogue."""
import os
import json
import re
import datetime
from pathlib import Path

from .agent import Agent, TmuxAgent, agent_dialogue
from .tools import (
    get_trend_data, generate_music, generate_music_batch, generate_image,
    create_video, upload_youtube
)
from .logger import MeetingLogger

INSTRUCTIONS_DIR = Path(__file__).parent.parent.parent / ".claude" / "agents"


def load_instructions(name: str) -> str:
    path = INSTRUCTIONS_DIR / f"{name}.md"
    if not path.exists():
        return f"당신은 {name} 에이전트입니다. 최선을 다해 역할을 수행하세요."
    text = path.read_text(encoding="utf-8")
    # frontmatter(--- ... ---) 제거 후 실제 지침서 내용만 반환
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].lstrip("\n")
    return text


def _clean_title(raw: str) -> str:
    """에이전트 응답 원문에서 순수 제목만 추출."""
    # 따옴표 안 텍스트 우선 추출 ("..." 또는 "..." 형식)
    m = re.search(r'["“‘]([^"”’]{4,40})["”’]', raw)
    if m:
        return m.group(1).strip()
    # "컨셉 ①②③ ... 선택/채택/확정" 패턴에서 뒷부분 제거
    cleaned = re.sub(r'컨셉\s*[①②③④⑤\d]+\s*', '', raw)
    cleaned = re.sub(r'\s*(선택|채택|확정|진행|로\s*진행).*$', '', cleaned, flags=re.IGNORECASE)
    # **굵은 텍스트** 마크다운 제거
    cleaned = re.sub(r'\*+', '', cleaned).strip()
    # 남은 따옴표·괄호 제거
    cleaned = re.sub(r'["""\'()]', '', cleaned).strip()
    return cleaned[:40] if cleaned else raw[:40]


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
            val = m.group(1).strip()
            concept[key] = _clean_title(val) if key == "title" else val

    if not concept.get("title"):
        # 따옴표 안 텍스트에서 제목 추출 시도
        m = re.search(r'["“]([^"”]{4,40})["”]', text)
        if m:
            concept["title"] = m.group(1).strip()
        else:
            # 마지막 폴백: 첫 번째 짧은 줄
            for line in text.split("\n"):
                line = _clean_title(line.strip())
                if line and not line.startswith("#") and 4 <= len(line) <= 50:
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

    raw_title = title_m.group(1).strip() if title_m else None
    description = desc_m.group(1).strip() if desc_m else None

    # Ensure "Playlist | 제목" format — strip any leading emoji/prefix before Playlist
    title = None
    if raw_title:
        # 에이전트 컨셉 용어 포함 시 폴백으로 처리
        bad_patterns = [r'컨셉\s*\d+', r'컨셉\s*[①②③④⑤]', r'^\s*[①②③④⑤]']
        has_bad = any(re.search(p, raw_title, re.IGNORECASE) for p in bad_patterns)
        if not has_bad:
            # 이미 "Playlist |" 형식이면 그대로, 아니면 앞에 붙임
            if re.match(r'Playlist\s*\|', raw_title, re.IGNORECASE):
                title = raw_title
            else:
                # 이모지·채널명 prefix 제거 후 형식 적용
                clean = re.sub(r'^[\W\s]+', '', raw_title).strip()
                clean = re.sub(r'\|.*$', '', clean).strip()
                title = f"Playlist | {clean}" if clean else None

    # Fallback: "Playlist | {concept title}"
    if not title:
        base = concept.get("title", "감성 플레이리스트")
        # concept title도 컨셉 용어 포함 시 기본값 사용
        if re.search(r'컨셉\s*[\d①②③④⑤]', base, re.IGNORECASE):
            base = "감성 플레이리스트"
        title = f"Playlist | {base}"

    if not description:
        related = "\n".join([f"· {t}" for t in top_titles[:3]])
        description = (
            f"감성적인 음악 모음 🎵\n\n{related}\n\n"
            "📌 구독하고 매주 새로운 플레이리스트를 받아보세요\n"
            "🔔 알림 설정 ON\n\n"
            "#플레이리스트 #감성음악 #KoreanPlaylist #ChillMusic #음악모음"
        )

    return {"title": title, "description": description}


def _save_state(state: dict, output_dir: str) -> None:
    """Persist pipeline state to output dir for dashboard."""
    try:
        path_local = os.path.join(output_dir, "state.json")
        with open(path_local, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_CHANNEL_FOLDER_MAP = {
    "DGM": "DGM_Playlist",
}
# WSL에서 접근 가능한 C: 드라이브 기반 프로젝트 경로
_PROJECTS_BASE = "/mnt/c/Users/오원진/AppData/Local/dgm_output/{ch_folder}/projects"


def run_pipeline(channel: str = "DGM", num_tracks: int = 20) -> dict:
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_only = datetime.datetime.now().strftime("%Y%m%d")
    ch_folder = _CHANNEL_FOLDER_MAP.get(channel, channel)
    projects_base = _PROJECTS_BASE.format(ch_folder=ch_folder)
    os.makedirs(projects_base, exist_ok=True)

    # 컨셉 확정 전까지 임시 폴더 사용 → Step 2 후 rename
    temp_dir = os.path.join(projects_base, f"_tmp_{date_str}")
    os.makedirs(temp_dir, exist_ok=True)
    output_dir_linux = temp_dir

    logger = MeetingLogger(output_dir_linux, channel, date_str)
    meeting_log: list = []

    state = {
        "channel": channel,
        "date": date_str,
        "outputDirLinux": output_dir_linux,
        "steps": {s: "pending" for s in
                  ["trend", "prompt", "music", "image", "video", "upload"]},
        "stepData": {},
        "startedAt": datetime.datetime.utcnow().isoformat() + "Z",
    }

    sep = "=" * 52
    print(f"\n{sep}")
    print(f"  DGM 파이프라인 시작: {channel}")
    print(f"  {date_str}")
    print(f"{sep}\n")

    # ── 실행 모드 감지: tmux "dgm" 세션이 실행 중이면 TmuxAgent 사용 ──────
    import subprocess as _sp
    _tmux_running = _sp.run(
        ["tmux", "list-sessions"], capture_output=True, text=True
    ).stdout
    USE_TMUX = "dgm" in _tmux_running
    AgentClass = TmuxAgent if USE_TMUX else Agent
    mode_name = "tmux 창 표시" if USE_TMUX else "Python SDK 직접"
    print(f"  에이전트 모드: {mode_name}")

    # ── 에이전트 초기화 (10개) ─────────────────────────────────────────
    orchestrator   = AgentClass("orchestrator",      load_instructions("orchestrator"))
    researcher     = AgentClass("researcher",         load_instructions("researcher"))
    strategist     = AgentClass("strategist",         load_instructions("strategist"))
    music_gen      = AgentClass("music-generator",    load_instructions("music-generator"))
    image_gen      = AgentClass("image-generator",    load_instructions("image-generator"))
    video_prod     = AgentClass("video-producer",     load_instructions("video-producer"))
    yt_uploader    = AgentClass("youtube-uploader",   load_instructions("youtube-uploader"))
    qa_inspector   = AgentClass("qa-inspector",       load_instructions("qa-inspector"))
    _qa_tester     = AgentClass("qa-tester",          load_instructions("qa-tester"))
    _sys_dev       = AgentClass("system-developer",   load_instructions("system-developer"))

    # ── Step 1: 트렌드 분석 ────────────────────────────────────────────
    print("[1/6] 트렌드 분석...")
    trend_data = get_trend_data()
    trend_videos = trend_data.get("trendVideos", [])[:5]
    top_titles = [v.get("title", "") for v in trend_videos]
    state["trendVideos"] = trend_videos
    state["topTitles"] = top_titles
    state["steps"]["trend"] = "done"
    state["stepData"]["trend"] = {"titles": top_titles}
    _save_state(state, output_dir_linux)
    print(f"  {len(top_titles)}개 트렌드 수집 완료")

    # ── Step 2: 컨셉 기획 (researcher → strategist) ───────────────────
    print("\n[2/6] 컨셉 기획 (researcher → strategist)...")
    trend_summary = "\n".join([f"- {t}" for t in top_titles]) or "- 감성적인 한국 플레이리스트"

    research_brief = (
        f"채널: {channel}\n"
        f"API로 수집된 트렌드 영상 제목들:\n{trend_summary}\n\n"
        "위 트렌드를 분석하고, strategist에게 전달할 요약을 포함한 컨셉 후보 3개를 제안해주세요."
    )
    research_result = researcher.chat(research_brief)
    logger.log("researcher", research_brief, research_result, 1)
    meeting_log.clear()

    initial_brief = (
        f"채널: {channel}\n"
        f"researcher 리포트:\n{research_result[:1000]}\n\n"
        "이 리포트를 바탕으로 최종 컨셉 1개를 확정하고 아래 형식으로 정확히 답하세요:\n"
        "- 제목: (한국어, 30자 이내)\n"
        "- 음악 스타일: (장르와 분위기, 영문)\n"
        "- 가이드: (영문 키워드, 50자 이내)\n"
        "- 분위기 키워드: (3개, 쉼표 구분)\n"
        "- musicDirection: (Suno AI용 구체적 악기·리듬 지시, 영문)\n"
        "- visualDirection: (이미지 생성용 장면·조명·색감 지시, 영문)"
    )

    music_concept_text = agent_dialogue(
        orchestrator, strategist, initial_brief, max_rounds=3, meeting_log=meeting_log
    )

    for entry in meeting_log:
        logger.log(entry["speaker"], "", entry["content"], entry["round"])
    meeting_log.clear()

    concept = parse_music_concept(music_concept_text)
    state["selectedPrompt"] = concept
    state["steps"]["prompt"] = "done"
    state["stepData"]["prompt"] = {"concept": concept, "rawText": music_concept_text[:800]}
    print(f"  컨셉 확정: {concept['title']}")

    # ── 임시 폴더 → 최종 이름으로 rename ────────────────────────────────
    clean_title = re.sub(r'[<>:"/\\|?*\n\r]', '_', concept["title"])[:30].strip().rstrip('_')
    folder_name = f"{clean_title}_{date_only}"
    final_dir = os.path.join(projects_base, folder_name)
    # 동일 이름 폴더 충돌 방지
    if os.path.exists(final_dir):
        final_dir = os.path.join(projects_base, f"{folder_name}_{date_str[-6:]}")
    try:
        os.rename(output_dir_linux, final_dir)
        output_dir_linux = final_dir
        logger.output_dir = final_dir
    except Exception as _rename_err:
        print(f"  폴더 rename 실패 ({_rename_err}), 임시 폴더 사용")
        output_dir_linux = temp_dir

    # 서브폴더 생성
    music_dir = os.path.join(output_dir_linux, "music")
    image_dir = os.path.join(output_dir_linux, "image")
    video_dir = os.path.join(output_dir_linux, "video")
    for d in [music_dir, image_dir, video_dir]:
        os.makedirs(d, exist_ok=True)

    state["outputDirLinux"] = output_dir_linux
    state["folderName"] = os.path.basename(output_dir_linux)
    _save_state(state, output_dir_linux)

    # ── Step 3: 음악 배치 생성 ────────────────────────────────────────
    mode_label = "테스트" if num_tracks <= 5 else "운영"
    print(f"\n[3/6] 음악 배치 생성 중... ({concept['title']}, {num_tracks}곡 {mode_label} 모드)")
    music_result = generate_music_batch(concept, music_dir, num_tracks=num_tracks)
    state["musicFile"] = music_result["music_path"]
    state["numTracks"] = music_result["music_info"]["totalTracks"]
    state["steps"]["music"] = "done"
    state["stepData"]["music"] = {
        "numTracks": state["numTracks"],
        "tracks": [{"num": t.get("trackNum"), "fileSizeMB": t.get("fileSizeMB")}
                   for t in music_result["music_info"].get("tracks", [])]
    }
    _save_state(state, output_dir_linux)
    print(f"  음악 완료: {music_result['music_path']} ({state['numTracks']}곡 연결)")

    # ── Step 4: 이미지 프롬프트 생성 (image-generator) ───────────────
    print("\n[4/6] 이미지 프롬프트 생성 (image-generator)...")
    image_brief = (
        f"음악 제목: {concept.get('title', '')}\n"
        f"스타일: {concept.get('style', '')}\n"
        f"분위기: {concept.get('mood', '')}\n"
        f"visualDirection: {concept.get('visualDirection', '')}\n\n"
        "이 음악에 어울리는 YouTube 배경 이미지 미드저니 프롬프트를 작성해주세요.\n"
        "영문 60-100 단어, cinematic·high quality·16:9 ratio·no text·no logo·"
        "empty lower area for title overlay 필수 포함."
    )

    image_prompt = agent_dialogue(
        orchestrator, image_gen, image_brief, max_rounds=3, meeting_log=meeting_log
    )

    for entry in meeting_log:
        logger.log(entry["speaker"], "", entry["content"], entry["round"])
    meeting_log.clear()

    state["imagePrompt"] = image_prompt

    print("  이미지 생성 중...")
    try:
        image_path = generate_image(image_prompt, image_dir)
        state["bgImagePath"] = image_path
        state["steps"]["image"] = "done"
        state["stepData"]["image"] = {"method": "ai", "path": image_path, "prompt": image_prompt[:200]}
        print(f"  이미지 완료: {image_path}")
    except Exception as e:
        print(f"  이미지 API 실패: {e} — 기본 배경 생성")
        from .tools import _fallback_image
        image_path = _fallback_image(image_dir)
        state["bgImagePath"] = image_path
        state["steps"]["image"] = "done"
        state["stepData"]["image"] = {"method": "fallback", "path": image_path, "error": str(e)}
    _save_state(state, output_dir_linux)

    # ── Step 5: 영상 제작 ──────────────────────────────────────────────
    print("\n[5/6] 영상 합성 중...")
    video_path = create_video(
        music_result["music_path"], image_path,
        video_dir, title=concept["title"]
    )
    state["videoPath"] = video_path
    state["steps"]["video"] = "done"
    state["stepData"]["video"] = {"path": video_path}
    _save_state(state, output_dir_linux)
    print(f"  영상 완료: {video_path}")

    # ── youtube-uploader: 메타데이터 생성 ────────────────────────────
    upload_meta_prompt = (
        f"채널: {channel}\n"
        f"음악 제목: {concept.get('title', '')}\n"
        f"스타일: {concept.get('style', '')}\n"
        f"분위기: {concept.get('mood', '')}\n"
        f"트렌드 참고: {', '.join(top_titles[:3])}\n\n"
        "아래 형식으로 정확히 답하세요:\n"
        "TITLE: (YouTube 업로드 제목, 50자 이내, 'Playlist |' 형식)\n"
        "DESCRIPTION: (설명문, 200자 이내, 해시태그 10개 이상 포함)"
    )
    upload_meta = yt_uploader.chat(upload_meta_prompt)
    logger.log("youtube-uploader", upload_meta_prompt, upload_meta, 0)

    # ── qa-inspector: 최종 검수 ───────────────────────────────────────
    qa_prompt = (
        f"출력 폴더: {output_dir_linux}\n"
        f"음악 파일: {music_result['music_path']}\n"
        f"이미지 파일: {image_path}\n"
        f"영상 파일: {video_path}\n"
        f"업로드 제목: (아래 메타데이터에서 추출)\n{upload_meta[:500]}\n\n"
        "위 산출물을 검수하고 PASS / WARN / FAIL 중 하나로 판정하세요."
    )
    qa_result = qa_inspector.chat(qa_prompt)
    logger.log("qa-inspector", qa_prompt, qa_result, 0)
    state["qaResult"] = qa_result[:200]

    upload_info = parse_upload_info(upload_meta, concept, top_titles)
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
            state["stepData"]["upload"] = {"url": yt_url, "title": upload_info["title"]}
            state["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            _save_state(state, output_dir_linux)
            print(f"  ✅ 업로드 완료: {yt_url}")
        else:
            raise RuntimeError(str(result))
    except Exception as e:
        state["steps"]["upload"] = "error"
        state["uploadError"] = str(e)
        state["status"] = "upload_failed"
        state["stepData"]["upload"] = {"error": str(e)}
        _save_state(state, output_dir_linux)
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
