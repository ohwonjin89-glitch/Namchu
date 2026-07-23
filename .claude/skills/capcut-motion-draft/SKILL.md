---
name: capcut-motion-draft
description: CapCut 초안의 배경이 정지 이미지가 아니라 짧은 반복 동영상 클립(예 DGM_MOTION_TEMPLATE)일 때, 그 클립을 노래 전체 길이에 맞춰 반복 복사해서 채운다. "모션 영상 초안 만들어줘", "동영상 길이 늘려줘/반복해줘", "노래 길이에 맞춰줘" 같은 요청에 사용.
---

CapCut 초안에 짧은 움직이는 mp4 클립(배경 동영상, 보통 몇 초짜리)과 노래(오디오 트랙, 이미 전체 길이만큼 배치됨)가 함께 들어있을 때, 그 짧은 클립을 처음부터 반복 재생하는 세그먼트들로 이어붙여 노래 전체 길이를 채운다.

## 전제 조건

- 대상 CapCut 초안이 `C:\Users\<user>\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\<초안이름>\`에 이미 존재
- 그 초안의 video 트랙 중 하나가:
  - 소재 타입이 `"type": "video"` (정지 이미지인 `"photo"` 아님)
  - 세그먼트 길이가 draft 전체 길이(`draft["duration"]`, = 오디오 총 길이)보다 짧음
- (로고/워터마크 같은 `photo` 타입의 video 트랙이 같이 있어도 무방 — 자동으로 건너뜀)

## 실행

```
python "C:\suno-api\scripts\loop_capcut_video_track.py" --draft "<초안 폴더명>"
```

예:
```
python "C:\suno-api\scripts\loop_capcut_video_track.py" --draft "DGM_MOTION_TEMPLATE"
```

## 동작 방식

1. `draft_content.json`을 읽어 전체 길이(`duration`, 오디오 총합과 동일)를 확인
2. video 트랙 중 소재 `type=="video"`이고 세그먼트 길이가 전체보다 짧은 것을 자동으로 찾음
3. 그 클립 길이(`clip_us`)로 전체 길이를 나눠 풀루프 횟수 + 마지막 부분루프(나머지)를 계산
4. 각 루프마다 `source_timerange`를 `{start:0, duration:...}`로 리셋한 새 세그먼트를 만들어 순서대로 이어붙임 (매 루프 클립 처음부터 재생 = 반복 재생 효과)
5. 세그먼트 길이 합이 draft 전체 길이와 정확히 일치하는지 assert로 검증
6. 수정 전 `draft_content.json`을 같은 폴더에 `draft_content_<HHMMSS>.json`으로 백업한 뒤 덮어씀

## 확인

CapCut을 열어 해당 초안의 재생 바를 스크럽해 보면서 클립이 끊김 없이 반복되는지, 마지막 부분(나머지 구간)이 어색하게 끊기지 않는지 확인한다. 문제가 있으면 백업 파일(`draft_content_<HHMMSS>.json`)을 `draft_content.json`으로 복원하면 원상복구된다.

## 참고

- 정지 이미지 배경 CapCut 초안(레퍼런스: `Z:\...\capcut-draft-producer\_capcut_config.json` 기반)을 새로 만드는 것은 이 스킬이 아니라 `make_capcut_draft.py`(`C:\suno-api\scripts\make_capcut_draft.py`) 담당 — 이 스킬은 이미 만들어진 초안의 "짧은 동영상 배경을 늘리는" 후처리 단계다.
- CapCut 초안이 `Z:\` (rclone VPS 마운트) 경로의 미디어를 직접 참조하면 열 때마다 네트워크로 스트리밍해서 매우 느려진다 — mp3/이미지 소재는 항상 로컬(`C:\temp_dgm_upload\<project>\...`)로 복사한 뒤 그 경로로 초안을 만들 것.
