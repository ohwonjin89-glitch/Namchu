#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loop_capcut_video_track.py — CapCut 초안의 짧은 반복영상 트랙을 오디오(전체 영상) 길이에 맞춰 반복 복사.

DGM_MOTION_TEMPLATE처럼 배경이 정지 이미지 대신 짧은 움직이는 mp4 클립인 경우,
그 클립 하나만으로는 노래 전체 길이를 못 채우므로 같은 소재를 처음부터 반복 재생하는
세그먼트를 이어붙여 draft duration(오디오 총 길이)까지 채운다.

Usage:
  python loop_capcut_video_track.py --draft <초안 폴더명>
"""

import argparse
import copy
import io
import json
import os
import shutil
import sys
import time
import uuid

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CAPCUT_DRAFT_BASE = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "AppData", "Local", "CapCut", "User Data", "Projects", "com.lveditor.draft",
)


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def find_mat(materials: dict, mat_id: str) -> dict | None:
    for group in materials.values():
        if not isinstance(group, list):
            continue
        for m in group:
            if isinstance(m, dict) and m.get("id") == mat_id:
                return m
    return None


def main():
    ap = argparse.ArgumentParser(description="CapCut 반복영상 트랙을 전체 길이에 맞춰 루프")
    ap.add_argument("--draft", required=True, help="CapCut 초안 폴더명 (com.lveditor.draft 하위)")
    args = ap.parse_args()

    draft_dir = os.path.join(CAPCUT_DRAFT_BASE, args.draft)
    content_path = os.path.join(draft_dir, "draft_content.json")
    if not os.path.exists(content_path):
        raise SystemExit(f"❌ 초안 없음: {content_path}")

    with open(content_path, "r", encoding="utf-8") as f:
        draft = json.load(f)

    total_us = draft["duration"]
    print(f"전체 영상(오디오) 길이: {total_us/1_000_000:.2f}초")

    # 실제 동영상(정지 이미지 아님) 소재를 쓰는 video 트랙 찾기
    target_track = None
    target_mat = None
    for t in draft["tracks"]:
        if t["type"] != "video" or not t["segments"]:
            continue
        seg0 = t["segments"][0]
        mat = find_mat(draft["materials"], seg0["material_id"])
        if mat and mat.get("type") == "video" and seg0["target_timerange"]["duration"] < total_us:
            target_track = t
            target_mat = mat
            break

    if not target_track:
        raise SystemExit("❌ 반복할 대상 동영상 트랙을 찾지 못함 (type='video'이고 길이가 전체보다 짧은 세그먼트 없음)")

    orig_seg = target_track["segments"][0]
    clip_us = orig_seg["source_timerange"]["duration"]
    print(f"반복 대상 클립: {target_mat.get('material_name')} ({clip_us/1_000_000:.2f}초)")

    n_full, remainder = divmod(total_us, clip_us)
    n_segments = n_full + (1 if remainder else 0)
    print(f"반복 횟수: {n_full}회 풀루프 + {'1회 부분루프(' + str(round(remainder/1_000_000,2)) + '초)' if remainder else '없음'} = 총 {n_segments}개 세그먼트")

    new_segs = []
    cursor = 0
    for i in range(n_segments):
        dur = clip_us if (i < n_full) else remainder
        seg = copy.deepcopy(orig_seg)
        seg["id"] = new_id()
        seg["target_timerange"] = {"start": cursor, "duration": dur}
        seg["source_timerange"] = {"start": 0, "duration": dur}
        new_segs.append(seg)
        cursor += dur

    assert cursor == total_us, f"길이 불일치: {cursor} != {total_us}"

    target_track["segments"] = new_segs

    ts = time.strftime("%H%M%S")
    backup_path = os.path.join(draft_dir, f"draft_content_{ts}.json")
    shutil.copy2(content_path, backup_path)
    print(f"백업: {backup_path}")

    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False)

    print(f"✅ 완료 — {len(new_segs)}개 세그먼트로 영상 트랙을 채웠습니다.")


if __name__ == "__main__":
    main()
