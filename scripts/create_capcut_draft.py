# -*- coding: utf-8 -*-
"""
CapCut 초안 자동 생성 스크립트
사용법: python create_capcut_draft.py <json_params>
"""
import sys, json, os

def create_draft(params: dict) -> dict:
    from pycapcut import DraftFolder
    from pycapcut.local_materials import VideoMaterial, AudioMaterial
    from pycapcut.video_segment import VideoSegment
    from pycapcut.audio_segment import AudioSegment
    from pycapcut.text_segment import TextSegment, TextStyle
    from pycapcut.segment import ClipSettings
    from pycapcut.track import TrackType
    from pycapcut.time_util import Timerange

    draft_folder_path = params.get("draftFolderPath", r"C:\Users\오원진\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
    draft_name        = params.get("draftName", "AI_Studio_Draft")
    bg_image_path     = params.get("bgImagePath", "")
    bg_video_path     = params.get("bgVideoPath", "")
    music_files       = params.get("musicFiles", [])   # [{"path": "...", "title": "..."}]
    logo_path         = params.get("logoPath", "")
    text_overlays     = params.get("textOverlays", [])
    width             = params.get("width", 1920)
    height            = params.get("height", 1080)
    fps               = params.get("fps", 30)

    if not music_files:
        return {"error": "음악 파일이 없습니다."}

    # 전체 길이 계산 (음악 파일 길이 합산)
    import pymediainfo
    total_duration_ms = 0
    music_durations = []
    for mf in music_files:
        path = mf.get("path", "")
        if not os.path.exists(path):
            return {"error": f"음악 파일을 찾을 수 없습니다: {path}"}
        try:
            mi = pymediainfo.MediaInfo.parse(path)
            dur_ms = int(mi.tracks[0].duration or 0)
        except Exception:
            dur_ms = 180000  # 기본 3분
        music_durations.append(dur_ms)
        total_duration_ms += dur_ms

    if total_duration_ms == 0:
        return {"error": "음악 길이를 읽을 수 없습니다."}

    total_us = total_duration_ms * 1000  # microseconds

    # 초안 생성
    df = DraftFolder(draft_folder_path)
    script = df.create_draft(draft_name, width, height, fps, allow_replace=True)

    # ── 1. 배경 트랙 (이미지 또는 영상) ─────────────────────────
    bg_path = bg_video_path if bg_video_path and os.path.exists(bg_video_path) else bg_image_path
    if bg_path and os.path.exists(bg_path):
        script.add_track(TrackType.video, "background")
        bg_mat = VideoMaterial(bg_path)
        seg = VideoSegment(bg_mat, Timerange(0, total_us))
        script.add_segment(seg, "background")

    # ── 2. 음악 트랙 (파일별 순차 배치) ─────────────────────────
    script.add_track(TrackType.audio, "music")
    cursor_us = 0
    for i, mf in enumerate(music_files):
        path = mf.get("path", "")
        dur_us = music_durations[i] * 1000
        audio_mat = AudioMaterial(path)
        seg = AudioSegment(audio_mat, Timerange(cursor_us, dur_us))
        script.add_segment(seg, "music")
        cursor_us += dur_us

    # ── 3. 로고 오버레이 ─────────────────────────────────────────
    if logo_path and os.path.exists(logo_path):
        logo_scale = params.get("logoScale", 0.38)
        script.add_track(TrackType.video, "logo", relative_index=1)
        logo_mat = VideoMaterial(logo_path)
        logo_seg = VideoSegment(
            logo_mat,
            Timerange(0, total_us),
            clip_settings=ClipSettings(
                scale_x=logo_scale,
                scale_y=logo_scale,
                transform_x=params.get("logoX", 0.0),
                transform_y=params.get("logoY", -0.42),
                alpha=params.get("logoAlpha", 1.0),
            )
        )
        script.add_segment(logo_seg, "logo")

    # ── 4. 텍스트 오버레이 ───────────────────────────────────────
    if text_overlays:
        script.add_track(TrackType.text, "text_overlay")
        for ot in text_overlays:
            start_us = int(ot.get("startMs", 0)) * 1000
            end_us   = int(ot.get("endMs", total_duration_ms)) * 1000
            dur_us   = end_us - start_us
            if dur_us <= 0:
                continue
            style = TextStyle(
                size=float(ot.get("size", 8.0)),
                bold=ot.get("bold", False),
                color=tuple(ot.get("color", [1.0, 1.0, 1.0])),
                alpha=float(ot.get("alpha", 1.0)),
            )
            seg = TextSegment(
                text=ot.get("text", ""),
                timerange=Timerange(start_us, dur_us),
                style=style,
            )
            script.add_segment(seg, "text_overlay")

    # ── 5. 저장 ─────────────────────────────────────────────────
    script.save()

    draft_path = os.path.join(draft_folder_path, draft_name)
    return {
        "success": True,
        "draftPath": draft_path,
        "draftName": draft_name,
        "totalDurationMs": total_duration_ms,
        "trackCount": len(music_files),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "사용법: python create_capcut_draft.py <JSON문자열> 또는 --params-file <경로>"}))
        sys.exit(1)
    try:
        if sys.argv[1] == "--params-file":
            if len(sys.argv) < 3:
                raise ValueError("--params-file 뒤에 파일 경로가 필요합니다.")
            with open(sys.argv[2], encoding="utf-8") as f:
                params = json.load(f)
        else:
            params = json.loads(sys.argv[1])
        result = create_draft(params)
    except Exception as e:
        result = {"error": str(e)}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
