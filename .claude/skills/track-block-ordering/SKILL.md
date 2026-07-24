---
name: track-block-ordering
description: music_info.json의 30개 트랙(선정 15 + 비선정 15)을 최종 영상/CapCut 초안용 순서로 배열하는 공용 알고리즘 — 선정 블록 우선, lyricsStartsImmediately 우선 정렬, 파일명 번호 기준 정렬. video-producer와 capcut-draft-producer가 동일하게 사용한다.
---

# 트랙 블록 순서 결정

video-producer(FFmpeg 모드)와 capcut-draft-producer(CapCut 모드)는 둘 다 `music-generator/music_info.json`의 트랙 배열을 최종 재생 순서로 변환해야 한다. 두 에이전트는 서로 다른 산출물(`track_order.json` vs `_capcut_config.json`의 `musicFiles`)을 만들지만 순서를 정하는 규칙은 동일하다 — 이 스킬이 그 공통 규칙이다.

## 규칙 (3가지, 순서대로 적용)

1. **선정 블록이 항상 먼저, 비선정 블록이 이어서.** `usage: "selected"` 트랙 전체(보통 01~15번)를 먼저 배치하고, `usage: "rejected"` 트랙 전체(보통 16~30번)를 그 뒤에 이어붙인다. 곡마다 A/B를 번갈아 배치하지 않는다 — 같은 호출에서 나온 선정/비선정 쌍이 인접하지 않도록 블록 단위로 분리하는 것이 의도된 설계다.
2. **각 블록 내부는 `lyricsStartsImmediately: true`인 트랙을 먼저.** 가사가 즉시 시작하는 곡을 블록 앞쪽에 배치하면 플레이리스트 초반 임팩트가 좋다. (video-producer만 적용 — capcut-draft-producer의 간이 버전은 이 서브정렬 없이 파일명 순서만 사용해도 무방하다.)
3. **동률이면 파일명의 트랙 번호(prefix)로 정렬.** `01_`, `02_` 같은 파일명 앞자리 숫자를 기준 정렬키로 쓴다.

## 공통 Python 스니펫

```python
import json

info = json.load(open(f"{PROJECT_DIR}/music-generator/music_info.json"))
tracks = info["tracks"]

# qa-inspector가 격리했거나 파일이 없는 트랙은 제외 (video-producer 전용 — capcut 모드는 생략 가능)
# tracks = [t for t in tracks if t.get("quarantined") is not True and os.path.exists(...)]

selected_tracks = sorted(
    [t for t in tracks if t.get("usage") == "selected"],
    key=lambda t: (not t.get("lyricsStartsImmediately", False), t["filename"]),
)
rejected_tracks = sorted(
    [t for t in tracks if t.get("usage") == "rejected"],
    key=lambda t: (not t.get("lyricsStartsImmediately", False), t["filename"]),
)
fallback_tracks = [t for t in tracks if t.get("usage") not in ("selected", "rejected")]

ordered_tracks = selected_tracks + rejected_tracks + fallback_tracks
print("선정 블록:", len(selected_tracks), "/ 비선정 블록:", len(rejected_tracks), "/ 합계:", len(ordered_tracks))
# → 합계가 30이 아니면 (qa-inspector 격리 케이스가 아닌 한) 원인을 확인하고 진행한다.
```

`lyricsStartsImmediately`를 서브정렬로 쓰지 않는 단순 버전(capcut-draft-producer가 쓰는 간이형)이 필요하면 `key=lambda t: t["filename"]`만 사용해도 된다 — 다만 video-producer와의 순서 일관성이 필요한 프로젝트라면 동일한 정렬키를 쓰는 쪽을 권장한다.

## 각 에이전트의 산출물 형식

- **video-producer**: `ordered_tracks`를 `track_order.json`으로 저장 — `[{"title": ..., "filename": "selected/{...}.mp3"}, ...]`. 이 파일은 youtube-uploader가 타임스탬프 댓글을 계산할 때 참조한다.
- **capcut-draft-producer**: `ordered_tracks`를 `_capcut_config.json`의 `musicFiles` 배열로 직접 사용 — `[{"path": "Z:\\...\\selected\\01_....mp3", "title": ...}, ...]` (Z:\ 경로 변환은 별도 처리). CapCut 모드에서는 video-producer가 실행되지 않으므로 `track_order.json`이 없는 것이 정상이며, 이를 이유로 15곡으로 줄이면 안 된다 — 항상 `music_info.json`에서 직접 30곡 전체를 계산한다.

## 검증

두 에이전트 모두 최종 배열 개수가 기대치(기본 30, 또는 music-generator 호출 횟수 N에 따라 2N)와 일치하는지 assert로 확인한 뒤 다음 단계로 진행한다.

```python
assert len(ordered_tracks) == expected_total, f"{expected_total}곡이어야 하는데 {len(ordered_tracks)}곡 — selected/rejected 블록 중 하나가 누락되었을 가능성"
```
