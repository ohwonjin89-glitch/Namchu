#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_capcut_draft.py  —  Tasty Music 채널 CapCut 초안 자동 생성
Usage:
  python make_capcut_draft.py --config <_config.json 경로> [--name <초안이름>]
"""

import argparse
import copy
import io
import json
import math
import os
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

# Windows PowerShell stdout에서 이모지 출력 가능하도록 강제 UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from pymediainfo import MediaInfo as _MediaInfo
    _HAS_MEDIAINFO = True
except ImportError:
    _HAS_MEDIAINFO = False

# ── 상수 ────────────────────────────────────────────────────────────────────
SPECTRUM_STICKER_ID = "7460473405519744309"   # CapCut 내장 스펙트럼 스티커 ID
CAPCUT_DRAFT_BASE = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "AppData", "Local", "CapCut", "User Data", "Projects", "com.lveditor.draft",
)
SAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# 채널별 템플릿 설정
CHANNEL_CONFIGS = {
    "tastymusic": {
        "template":        "TASTYMUSIC_TEMPLATE",
        "text_alignment":  0,      # 좌측
        "spectrum_mode":   "webm_to_sticker",  # WEBM 트랙 제거 후 스티커로 교체
    },
    "dgm": {
        "template":        "DGM_TEMPLATE",
        "text_alignment":  None,   # 템플릿 그대로 유지 (center)
        "spectrum_mode":   "sticker_in_template",  # 이미 스티커, duration만 갱신
    },
    "playlisttan": {
        "template":        "Playlisttann_Template",
        "text_alignment":  None,   # 템플릿 그대로 유지 (center)
        "spectrum_mode":   "sticker_in_template",  # 이미 스티커, duration만 갱신 (DGM_TEMPLATE과 동일 구조, 로고만 playlisttann_white_transparent_clean.png로 교체)
    },
}


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def new_id() -> str:
    return str(uuid.uuid4()).upper()


def get_audio_duration_us(path: str) -> int:
    """오디오 파일의 실제 재생 가능한 길이를 마이크로초로 반환.

    mediainfo/ffprobe의 헤더 메타데이터를 그대로 쓰지 않는다 — Suno가 내려주는 mp3의
    VBR 헤더가 부정확하면 헤더 길이가 실제보다 짧게 보고될 수 있고, 그 값을 그대로
    CapCut 세그먼트 길이(target_timerange)로 넣으면 실제 곡이 끝나기 전에 다음 트랙으로
    넘어가 노래가 중간에 잘려서 재생되는 사고로 이어진다(2026-07-21 확인). 그래서 ffmpeg로
    끝까지 디코딩한 실측 길이를 우선 사용하고, 디코딩이 실패했을 때만 헤더 값으로 대체한다.
    """
    import subprocess

    decoded_us = 0
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        matches = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", r.stderr)
        if matches:
            h, m, s = matches[-1]
            decoded_us = int((int(h) * 3600 + int(m) * 60 + float(s)) * 1_000_000)
    except Exception as e:
        print(f"  ⚠ ffmpeg 실측 실패 ({os.path.basename(path)}): {e}")

    header_us = 0
    if _HAS_MEDIAINFO:
        try:
            info = _MediaInfo.parse(path)
            for track in info.tracks:
                if track.track_type in ("Audio", "General") and track.duration:
                    header_us = int(float(track.duration) * 1000)
                    break
        except Exception as e:
            print(f"  ⚠ mediainfo 실패 ({os.path.basename(path)}): {e}")

    if not header_us:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                capture_output=True, text=True, timeout=15
            )
            d = json.loads(r.stdout)
            header_us = int(float(d["format"]["duration"]) * 1_000_000)
        except Exception as e:
            print(f"  ⚠ ffprobe 실패 ({os.path.basename(path)}): {e}")

    if decoded_us:
        if header_us and abs(decoded_us - header_us) > 2_000_000:
            print(f"  ⚠ 헤더/실측 길이 불일치 ({os.path.basename(path)}): "
                  f"헤더 {header_us/1_000_000:.1f}s vs 실측 {decoded_us/1_000_000:.1f}s → 실측값 사용")
        return decoded_us
    return header_us


def find_mat(lst: list, mat_id: str) -> dict | None:
    return next((m for m in lst if m.get("id") == mat_id), None)


# ── 소재 / 세그먼트 빌더 ──────────────────────────────────────────────────────
def make_bg_material(template_mat: dict, img_path: str, duration_us: int) -> dict:
    mat = copy.deepcopy(template_mat)
    mat["id"]            = new_id()
    mat["path"]          = img_path.replace("\\", "/")
    mat["duration"]      = duration_us
    mat["material_name"] = os.path.basename(img_path)
    return mat


def make_audio_material(template_mat: dict, mp3_path: str, duration_us: int) -> dict:
    mat = copy.deepcopy(template_mat)
    mat["id"]               = new_id()
    mat["local_material_id"] = str(uuid.uuid4())
    mat["music_id"]          = str(uuid.uuid4())
    mat["path"]              = mp3_path.replace("\\", "/")
    mat["name"]              = os.path.basename(mp3_path)
    mat["material_name"]     = os.path.basename(mp3_path)
    mat["duration"]          = duration_us
    mat["wave_points"]       = []
    return mat


def make_video_seg(template_seg: dict, mat_id: str,
                   start_us: int, dur_us: int) -> dict:
    seg = copy.deepcopy(template_seg)
    seg["id"]                  = new_id()
    seg["material_id"]         = mat_id
    seg["target_timerange"]    = {"start": start_us, "duration": dur_us}
    seg["source_timerange"]    = {"start": 0,        "duration": dur_us}
    return seg


def make_audio_seg(template_seg: dict, mat_id: str,
                   start_us: int, dur_us: int) -> dict:
    seg = copy.deepcopy(template_seg)
    seg["id"]               = new_id()
    seg["material_id"]      = mat_id
    seg["target_timerange"] = {"start": start_us, "duration": dur_us}
    seg["source_timerange"] = {"start": 0,        "duration": dur_us}
    return seg


def _find_sticker_cache_path() -> str:
    """로컬 캐시에서 스펙트럼 스티커 경로 탐색."""
    import glob
    cache_dir = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        "AppData", "Local", "CapCut", "User Data", "Cache", "artistEffect",
        SPECTRUM_STICKER_ID,
    )
    matches = glob.glob(os.path.join(cache_dir, "*"))
    if matches:
        return matches[0].replace("\\", "/")
    return ""


def _make_spectrum_sticker(total_us: int, ref_seg: dict) -> tuple[dict, dict, dict]:
    """스펙트럼 스티커 소재·세그먼트·트랙을 생성해 반환."""
    mat_id = new_id()

    # ── 소재 ──
    mat = {
        "id": mat_id, "unique_id": "", "type": "sticker",
        "path": _find_sticker_cache_path(),
        "sticker_id": SPECTRUM_STICKER_ID,
        "resource_id": SPECTRUM_STICKER_ID,
        "name": "Interface EN Music Sound Waveform White",
        "category_id": "100000", "category_name": "",
        "platform": "all", "unicode": "", "source_platform": 1,
        "formula_id": "", "check_flag": 1, "team_id": "",
        "request_id": "", "combo_info": {"text_templates": []},
        "sub_type": 0,
        "radius": {"top_left": 0.0, "top_right": 0.0, "bottom_left": 0.0, "bottom_right": 0.0},
        "global_alpha": 1.0, "background_color": "", "background_alpha": 1.0,
        "border_line_style": 0, "border_width": 0.0, "border_color": "",
        "has_shadow": False, "shadow_color": "", "shadow_alpha": 0.8,
        "shadow_smoothing": 0.0, "shadow_distance": 0.0,
        "shadow_point": {"x": 0.0, "y": 0.0}, "shadow_angle": 0.0,
        "shape_param": {"shape_type": 0, "roundness": [], "custom_points": [], "shape_size": []},
        "original_size": [], "update_params": "", "aigc_type": "none",
        "sequence_type": False,
        "cycle_setting": True,   # ← 자동 루프 핵심
        "shape_fill_render_style": {
            "color": {
                "solid": {"color": "#FFFFFF", "alpha": 1.0},
                "gradient": {"color": [], "alpha": [], "percent": [],
                             "angle": 90.0, "mode": "all", "style": "linear"},
                "texture": {"path": "", "flip": [], "scale": 1.0, "alpha": 1.0,
                            "angle": 90.0, "blend": "no", "range": 4, "fill": "tile",
                            "resource_id": "", "effect_id": "", "play_speed": 1.0},
                "render_type": "solid",
            },
            "alpha": 1.0,
        },
        "shape_fill_use_flower_color": False,
        "multi_language_current": "none", "corner_pin": None,
        "icon_url": "", "preview_cover_url": "",
    }

    # ── 세그먼트 (WEBM 기존 위치 재사용, source_timerange=null → 무한 루프) ──
    seg = {
        "id": new_id(), "source_timerange": None,
        "target_timerange": {"start": 0, "duration": total_us},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "", "state": 0, "speed": 1.0,
        "is_loop": False, "is_tone_modify": False, "reverse": False,
        "intensifies_audio": False, "cartoon": False,
        "volume": 1.0, "last_nonzero_volume": 1.0,
        "clip": {                        # SPECTRUM_STICKER_TEST에서 사용자가 설정한 크기/위치
            "scale": {"x": 0.3619733945153285, "y": 0.3619733945153285},
            "rotation": 0.0,
            "transform": {"x": 0.46197916666666666, "y": -0.6564814814814814},
            "flip": {"vertical": False, "horizontal": False},
            "alpha": 1.0,
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "material_id": mat_id, "extra_material_refs": [],
        "render_index": 14001,   # 스티커 레이어는 반드시 14001+ (비디오=1이면 스케일 재계산됨)
        "keyframe_refs": [], "enable_lut": False,
        "enable_adjust": False, "enable_hsl": False, "visible": True,
        "group_id": "", "enable_color_curves": True, "enable_hsl_curves": True,
        "track_render_index": 2,
        "hdr_settings": None, "enable_color_wheels": True, "track_attribute": 0,
        "is_placeholder": False, "template_id": "",
        "enable_smart_color_adjust": False, "template_scene": "default",
        "common_keyframes": [], "caption_info": None,
        "responsive_layout": {"enable": False, "target_follow": "",
                              "size_layout": 0, "horizontal_pos_layout": 0,
                              "vertical_pos_layout": 0},
        "enable_color_match_adjust": False, "enable_color_correct_adjust": False,
        "enable_adjust_mask": False, "raw_segment_id": "", "lyric_keyframes": None,
        "enable_video_mask": True, "digital_human_template_group_id": "",
        "color_correct_alg_result": "", "source": "segmentsourcenormal",
        "enable_mask_stroke": False, "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }

    # ── 트랙 ──
    track = {
        "id": new_id(), "type": "sticker",
        "flag": 0, "attribute": 0, "name": "", "is_default_name": True,
        "segments": [seg],
    }

    return mat, seg, track


# ── 메인 ─────────────────────────────────────────────────────────────────────
def make_capcut_draft(config_path: str, draft_name: str | None = None,
                      channel: str = "tastymusic") -> str:

    ch_cfg = CHANNEL_CONFIGS.get(channel)
    if not ch_cfg:
        sys.exit(f"❌ 지원하지 않는 채널: {channel}  (지원: {list(CHANNEL_CONFIGS)})")
    template_name = ch_cfg["template"]
    print(f"📺 채널: {channel}  템플릿: {template_name}")

    # ── 1. Config 읽기 ──────────────────────────────────────────────────────
    config_path = os.path.abspath(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    bg_image       = cfg.get("bgImageUrl", "")
    music_files    = cfg.get("musicFiles", [])
    tracklist_text = cfg.get("tracklistOverlay", {}).get("text", "")

    if not bg_image or not os.path.exists(bg_image):
        sys.exit(f"❌ 배경 이미지 없음: {bg_image}")
    if not music_files:
        sys.exit("❌ musicFiles 비어있음")

    # ── 2. 음악 파일 duration 계산 ────────────────────────────────────────
    print(f"🎵 음악 파일 {len(music_files)}개 처리 중…")
    song_durations = []
    for mf in music_files:
        dur = get_audio_duration_us(mf["path"])
        print(f"   {os.path.basename(mf['path'])[:50]}: {dur/1_000_000:.1f}초")
        song_durations.append(dur)

    total_us = sum(song_durations)
    print(f"   총 길이: {total_us/1_000_000:.1f}초 ({total_us/60_000_000:.1f}분)")

    # ── 3. 트랙리스트 텍스트 자동 생성 ────────────────────────────────────
    if not tracklist_text:
        titles = []
        for mf in music_files:
            t = os.path.splitext(os.path.basename(mf.get("path", mf.get("title", ""))))[0]
            t = re.sub(r"^\d+[._\-\s]+", "", t).strip()
            titles.append(t)
        tracklist_text = "  ·  ".join(titles)

    preview = (tracklist_text[:80] + "…") if len(tracklist_text) > 80 else tracklist_text
    print(f"📝 트랙리스트: {preview}")

    # ── 4. 템플릿 JSON 로드 ────────────────────────────────────────────────
    template_path = os.path.join(CAPCUT_DRAFT_BASE, template_name, "draft_content.json")
    if not os.path.exists(template_path):
        sys.exit(f"❌ 템플릿 없음: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        draft = json.load(f)

    # ── 5. 트랙 식별 ─────────────────────────────────────────────────────
    video_tracks = sorted(
        [t for t in draft["tracks"] if t["type"] == "video"],
        key=lambda t: min(s.get("render_index", 0) for s in t["segments"]) if t["segments"] else 0
    )
    audio_track = [t for t in draft["tracks"] if t["type"] == "audio"][0]
    text_track  = [t for t in draft["tracks"] if t["type"] == "text"][0]

    bg_track     = video_tracks[0]                    # render_index=0
    logo_tracks  = video_tracks[1:]                   # render_index=1,2,… (로고 or WEBM)

    orig_bg_mat  = find_mat(draft["materials"]["videos"], bg_track["segments"][0]["material_id"])
    orig_bg_seg  = bg_track["segments"][0]
    orig_aud_mat = find_mat(draft["materials"]["audios"], audio_track["segments"][0]["material_id"])
    orig_aud_seg = audio_track["segments"][0]

    # ── 6. 배경 트랙 교체 ────────────────────────────────────────────────
    bg_mat = make_bg_material(orig_bg_mat, bg_image, total_us)

    if ch_cfg["spectrum_mode"] == "webm_to_sticker":
        # Tasty Music: video 소재 전부 초기화 (WEBM 스펙트럼 포함)
        draft["materials"]["videos"] = [bg_mat]
    else:
        # DGM: 로고 소재는 유지, bg만 교체
        logo_mat_ids = {s["material_id"] for t in logo_tracks for s in t["segments"]}
        logo_mats = [m for m in draft["materials"]["videos"] if m.get("id") in logo_mat_ids]
        draft["materials"]["videos"] = [bg_mat] + logo_mats

    draft["materials"]["audios"] = []

    bg_seg = make_video_seg(orig_bg_seg, bg_mat["id"], 0, total_us)
    bg_track["segments"] = [bg_seg]

    # ── 7. 로고 트랙 duration 갱신 (DGM 전용) ────────────────────────────
    if ch_cfg["spectrum_mode"] == "sticker_in_template":
        for logo_t in logo_tracks:
            seg = copy.deepcopy(logo_t["segments"][0])
            seg["target_timerange"] = {"start": 0, "duration": total_us}
            logo_t["segments"] = [seg]

    # ── 8. 오디오 트랙 교체 ───────────────────────────────────────────────
    new_audio_segs = []
    cursor = 0
    for i, mf in enumerate(music_files):
        dur = song_durations[i]
        aud_mat = make_audio_material(orig_aud_mat, mf["path"], dur)
        draft["materials"]["audios"].append(aud_mat)
        aud_seg = make_audio_seg(orig_aud_seg, aud_mat["id"], cursor, dur)
        new_audio_segs.append(aud_seg)
        cursor += dur
    audio_track["segments"] = new_audio_segs

    # ── 9. 스펙트럼 처리 ─────────────────────────────────────────────────
    if ch_cfg["spectrum_mode"] == "webm_to_sticker":
        # Tasty Music: WEBM 트랙 제거 → 새 스티커 트랙 추가
        webm_track = logo_tracks[0] if logo_tracks else None
        orig_spec_seg = webm_track["segments"][0] if webm_track else {}
        if webm_track:
            draft["tracks"] = [t for t in draft["tracks"] if t is not webm_track]
        draft["materials"]["chromas"] = []
        sticker_mat, _seg, sticker_track = _make_spectrum_sticker(total_us, orig_spec_seg)
        draft["materials"].setdefault("stickers", []).append(sticker_mat)
        draft["tracks"].append(sticker_track)
        print(f"   스티커: {sticker_mat['path'] or '(캐시 없음)'}")
    else:
        # DGM: 기존 스티커 트랙의 duration만 갱신
        for t in draft["tracks"]:
            if t["type"] == "sticker":
                seg = copy.deepcopy(t["segments"][0])
                seg["target_timerange"] = {"start": 0, "duration": total_us}
                t["segments"] = [seg]

    # ── 10. 텍스트 트랙 갱신 ─────────────────────────────────────────────
    txt_seg = copy.deepcopy(text_track["segments"][0])
    txt_seg["target_timerange"] = {"start": 0, "duration": total_us}
    text_track["segments"] = [txt_seg]

    txt_mat_id = txt_seg["material_id"]
    for mat in draft["materials"].get("texts", []):
        if mat.get("id") == txt_mat_id:
            try:
                content_obj = json.loads(mat["content"])
                content_obj["text"] = tracklist_text
                mat["content"] = json.dumps(content_obj, ensure_ascii=False)
            except Exception as e:
                print(f"  ⚠ 텍스트 소재 파싱 실패: {e}")
            if ch_cfg["text_alignment"] is not None:
                mat["alignment"] = ch_cfg["text_alignment"]
            break

    # 나머지 텍스트 트랙들도 영상 전체 길이로 duration 갱신
    for t in draft["tracks"]:
        if t["type"] == "text" and t is not text_track:
            for seg in t["segments"]:
                seg["target_timerange"]["duration"] = total_us

    # ── 11. 총 길이 갱신 ──────────────────────────────────────────────────
    draft["duration"] = total_us

    # ── 12. 초안 이름 결정 ────────────────────────────────────────────────
    if not draft_name:
        project_dir = Path(config_path).parent.parent
        draft_name = project_dir.name

    safe_name = SAFE_NAME_RE.sub("_", draft_name)[:80]

    # ── 13. 새 초안 폴더 생성 + 파일 복사 ────────────────────────────────
    new_draft_dir = os.path.join(CAPCUT_DRAFT_BASE, safe_name)
    os.makedirs(new_draft_dir, exist_ok=True)

    template_dir = os.path.join(CAPCUT_DRAFT_BASE, template_name)
    for fname in os.listdir(template_dir):
        if fname == "draft_content.json":
            continue
        src = os.path.join(template_dir, fname)
        dst = os.path.join(new_draft_dir, fname)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

    meta_path = os.path.join(new_draft_dir, "draft_meta_info.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["id"]   = new_id()
            meta["name"] = safe_name
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ⚠ draft_meta_info.json 갱신 실패: {e}")

    out_json = os.path.join(new_draft_dir, "draft_content.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False)

    _register_to_root_meta(new_draft_dir, safe_name, new_id(), total_us)

    print(f"\n✅ CapCut 초안 저장 완료!")
    print(f"   폴더  : {new_draft_dir}")
    print(f"   총 {len(music_files)}곡 / {total_us/60_000_000:.1f}분")
    print(f"\n👉 CapCut 실행 → 홈 화면에서 '{safe_name}' 초안 확인")

    return out_json


def _register_to_root_meta(draft_dir: str, draft_name: str, draft_id: str, duration_us: int):
    """root_meta_info.json 의 all_draft_store 맨 앞에 새 항목 추가."""
    root_meta_path = os.path.join(CAPCUT_DRAFT_BASE, "root_meta_info.json")
    if not os.path.exists(root_meta_path):
        print("  ⚠ root_meta_info.json 없음 — 등록 건너뜀")
        return

    try:
        with open(root_meta_path, "r", encoding="utf-8") as f:
            root_meta = json.load(f)

        # 경로 형식 맞추기 (CapCut 스타일: 폴더는 /, 파일 결합은 \\)
        base_fwd = CAPCUT_DRAFT_BASE.replace("\\", "/")
        fold_path = f"{base_fwd}/{draft_name}"
        json_path = f"{base_fwd}/{draft_name}\\draft_content.json"
        cover_path = f"{base_fwd}/{draft_name}\\draft_cover.jpg"

        now_us = int(time.time() * 1_000_000)
        json_size = os.path.getsize(os.path.join(draft_dir, "draft_content.json"))

        new_entry = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": cover_path,
            "draft_fold_path": fold_path,
            "draft_id": draft_id,
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_json_file": json_path,
            "draft_name": draft_name,
            "draft_new_version": "",
            "draft_root_path": base_fwd,
            "draft_timeline_materials_size": json_size,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "pippit_avatar_url": "",
            "pippit_extra_info": "",
            "pippit_id": "",
            "pippit_user_name": "",
            "streaming_edit_draft_ready": True,
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
            "tm_draft_removed": 0,
            "tm_duration": duration_us,
        }

        store = root_meta.get("all_draft_store", [])
        # 동일 이름 기존 항목 제거 후 맨 앞에 삽입
        store = [e for e in store if e.get("draft_name") != draft_name]
        store.insert(0, new_entry)
        root_meta["all_draft_store"] = store
        root_meta["draft_ids"] = len(store)

        with open(root_meta_path, "w", encoding="utf-8") as f:
            json.dump(root_meta, f, ensure_ascii=False)

        print(f"   root_meta 등록 완료 (총 {len(store)}개 초안)")

    except Exception as e:
        print(f"  ⚠ root_meta_info.json 등록 실패: {e}")


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CapCut 초안 자동 생성")
    ap.add_argument("--config",  required=True, help="_config.json 경로")
    ap.add_argument("--name",    help="초안 이름 (생략 시 프로젝트 폴더명 사용)")
    ap.add_argument("--channel", default="tastymusic",
                    choices=list(CHANNEL_CONFIGS), help="채널 (기본: tastymusic)")
    args = ap.parse_args()

    make_capcut_draft(args.config, args.name, args.channel)
