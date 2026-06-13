---
name: api-reference
description: DGM 시스템 내 모든 API 명세. 에이전트 간 소통 시 이 파일의 코드명을 사용한다.
---

# DGM API 레퍼런스

모든 에이전트는 API를 언급할 때 아래 **코드명**을 사용한다.
베이스 URL: `http://172.28.32.1:3000` (WSL에서 Windows Next.js 서버 접근)

---

## 파이프라인 핵심 API

### 음악 생성 — music-generator 담당

| 코드명 | Method | Endpoint | 용도 |
|--------|--------|----------|------|
| `SUNO_GEN` | POST | `/api/custom_generate` | Suno 음악 생성 요청 (2곡 반환) |
| `SUNO_POLL` | GET | `/api/get?ids={id1,id2}` | 생성 상태 폴링 |

**SUNO_GEN 요청:**
```json
{
  "prompt": "분위기 설명 또는 가사 가이드",
  "tags": "Korean chill pop, emotional piano",
  "title": "영상 제목",
  "make_instrumental": true,
  "wait_audio": false
}
```
**SUNO_GEN 응답:** `[{"id": "...", "status": "queued"}, ...]`

**SUNO_POLL 응답:** `[{"id": "...", "status": "complete|streaming|error", "audio_url": "https://..."}]`
완료 상태: `complete` 또는 `streaming` + `audio_url` 존재

---

### 이미지 생성 — image-generator 담당

| 코드명 | Method | Endpoint | 용도 |
|--------|--------|----------|------|
| `NB2_GEN` | POST | `/api/nano-banana` | NB2(Evolink) 이미지 생성 요청 |
| `NB2_POLL` | GET | `/api/nano-banana?taskId={id}` | 생성 상태 폴링 |
| `MJ_GEN` | POST | `/api/midjourney` | Midjourney 이미지 생성 (고품질 필요 시) |

**NB2_GEN 요청:**
```json
{
  "prompt": "영문 이미지 프롬프트",
  "size": "16:9",
  "quality": "2K"
}
```
⚠️ `size`는 반드시 `"16:9"` (숫자 형식 `"1792x1024"` 사용 금지)
⚠️ `quality`는 반드시 `"2K"` (`"hd"` 사용 금지)

**NB2_GEN 응답:** `{"taskId": "task-unified-XXXX-YYYY"}`

**NB2_POLL 응답:**
```json
{ "status": "done|processing|error", "progress": 0~100, "imageUrl": "https://..." }
```

---

### 영상 합성 — video-producer 담당

| 코드명 | Method | Endpoint | 용도 |
|--------|--------|----------|------|
| `VIDEO_GEN` | POST | `/api/make-video` | 이미지+음악 → MP4 합성 요청 |
| `VIDEO_POLL` | GET | `/api/make-video?taskId={path}` | 합성 상태 폴링 |

**VIDEO_GEN 요청:**
```json
{
  "bgImagePath": "C:\\temp_dgm_upload\\background.jpg",
  "audioPath":   "C:\\temp_dgm_upload\\music.mp3",
  "outputDir":   "C:\\Users\\...\\출력폴더",
  "outputFileName": "playlist.mp4",
  "textOverlays": [{
    "text": "영상 제목",
    "fontFamily": "맑은 고딕", "fontSize": 52, "color": "#FFFFFF",
    "leftPct": 5, "topPct": 80, "widthPct": 90, "heightPct": 10, "bold": true
  }]
}
```
**VIDEO_GEN 응답:** `{"taskId": "C:\\...\\출력폴더"}` ← taskId는 outputDir 경로 그대로 사용
⚠️ 한글 경로 우회 필수 — 입력 파일은 반드시 `C:\temp_dgm_upload\`로 복사 후 전달

**VIDEO_POLL 응답:** `{"status": "done|error|starting", "progress": 0~100}`

---

### YouTube 업로드 — youtube-uploader 담당

| 코드명 | Method | Endpoint | 용도 |
|--------|--------|----------|------|
| `YT_UPLOAD` | POST | `/api/youtube-upload` | YouTube 비공개 업로드 |

**YT_UPLOAD 요청:**
```json
{
  "action": "upload",
  "channelKey": "DGM",
  "videoPath": "C:\\temp_dgm_upload\\upload.mp4",
  "title": "영상 제목 (50자 이내)",
  "description": "설명문\n\n#해시태그",
  "tags": ["플레이리스트", "감성음악", "KoreanPlaylist"],
  "privacyStatus": "private",
  "madeForKids": false
}
```
**채널 키:** `"DGM"` (DGM_Playlist 채널) / `"Playlisttann"` (Playlisttann 채널)
**YT_UPLOAD 응답:** `{"success": true, "videoId": "abc123", "url": "https://youtube.com/watch?v=abc123"}`

---

### YouTube 트렌드 — researcher 담당

| 코드명 | Method | Endpoint | 용도 |
|--------|--------|----------|------|
| `YT_TRENDS` | POST | `/api/youtube-trends` | YouTube 트렌드 영상 수집 |
| `TREND_CACHE` | GET | `/api/trend-cache` | 마지막 수집 결과 캐시 조회 |

**YT_TRENDS 요청:**
```json
{
  "action": "fetch_trends",
  "apiKey": "<YOUTUBE_API_KEY>",
  "days": 7,
  "minSubs": 5000
}
```
**YT_TRENDS 응답:** `{"trendVideos": [...], "keywords": [...], "competitorVideos": [...]}`

---

## 부가 API (필요 시 사용)

| 코드명 | Method | Endpoint | 담당 | 용도 |
|--------|--------|----------|------|------|
| `SUNO_LYRICS` | POST | `/api/generate_lyrics` | music-generator | 가사 자동 생성 |
| `SUNO_EXTEND` | POST | `/api/extend_audio` | music-generator | 음악 길이 연장 |
| `TOPIC_SUGGEST` | POST | `/api/suggest-topics` | strategist | AI 주제 제안 |
| `PROMPT_GEN` | POST | `/api/generate-prompts` | strategist/music-gen | 프롬프트 자동 생성 |
| `TREND_INSIGHT` | GET | `/api/trend-insight` | researcher | 트렌드 인사이트 분석 |
| `KLING_I2V` | POST | `/api/kling-i2v` | video-producer | Kling 이미지→영상 (움직임 효과) |

---

## 공통 규칙

1. **에이전트 간 API 언급 시 코드명 사용** — `NB2_GEN`, `SUNO_POLL` 등
2. **폴링 패턴**: 10초 간격, 최대 대기 시간 내 반복 → 초과 시 에러 처리
3. **한글 경로 우회**: 음악·이미지·영상 파일은 `/mnt/c/temp_dgm_upload/`로 복사 후 Windows 경로로 변환
4. **WSL ↔ Windows 경로 변환**: `/mnt/c/` → `C:\`

## 최대 폴링 대기 시간

| API | 최대 대기 |
|-----|---------|
| SUNO_GEN | 20분 (10초 × 120회) |
| NB2_GEN | 5분 (10초 × 30회) |
| VIDEO_GEN | 15분 (10초 × 90회) |
| YT_UPLOAD | 10분 (단일 요청, timeout=600s) |
