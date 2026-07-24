# 파이프라인 완료 보고서 (CapCut 모드)

프로젝트: 2026072301
완료 시각: 2026-07-23 12:00
pipelineMode: capcut

## 컨셉
- 제목: 밤에 혼자 듣기 좋은 감성 힙합 & 칠팝 플레이리스트
- 장르: Groove Hip-hop & Chill Pop (15곡)
- 이미지: Late Night R&B & Soul / 감성R&B 폴더 / 하이틴_4 sref (의도적 크로스 장르 테스트)

## CapCut 드래프트 파라미터
- 파라미터 파일: .claude/agents/projects/2026072301/capcut-draft-producer/_capcut_config.json
- 실행 가이드: .claude/agents/projects/2026072301/capcut-draft-producer/CAPCUT_GUIDE.md

## YouTube 메타데이터
- 메타데이터 문서: .claude/agents/projects/2026072301/youtube-uploader/_youtube_meta.md
- YouTube 제목: 𝐏𝐥𝐚𝐲𝐥𝐢𝐬𝐭 | 밤에 혼자 듣기 좋은 감성 힙합 & 칠팝 플레이리스트
- 트랙 수: 29곡 (선정 15 + 비선정 14, 1곡 too_short 격리)
- 전체 길이: 1시간 28분 27초

## QA ①음악 사전검수 결과
- 판정: WARN (통과)
- badTracks: 1 / 30 (badRatio 3.3% ≤ 10%)
- 격리 곡: 26_screen_glow_rej.mp3 (65.5초, too_short)
- 나머지 29곡 전량 이상 없음

## 사용자 다음 단계
1. Z:\ 드라이브 마운트 확인 (rclone mount vps-dgm:/ Z:\)
2. Windows에서 make_capcut_draft.py 실행 (CAPCUT_GUIDE.md 참조)
3. CapCut에서 편집 및 내보내기
4. _youtube_meta.md 참조하여 YouTube 업로드
