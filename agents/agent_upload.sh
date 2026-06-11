#!/bin/bash
# 업로드 에이전트
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"

log() { echo "[UPLOAD][$(date '+%H:%M:%S')] $1"; }

log "YouTube 업로드 시작..."

# 상태에서 정보 읽기
VIDEO_PATH=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('videoPath',''))")
TITLE_RAW=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('selectedPrompt',{}).get('title','감성 플레이리스트'))")

# 업로드 제목 포맷 (7가지 중 랜덤)
UPLOAD_TITLE=$(python3 -c "
import random, json
with open('$STATE_FILE') as f: d=json.load(f)
title = d.get('selectedPrompt',{}).get('title','감성 플레이리스트')
top = d.get('topTitles', [])
formats = [
    f'Playlist | {title}',
    f'{title} | 감성 플레이리스트 🎵',
    f'🎧 {title} playlist',
    f'[Playlist] {title}',
    f'{title} | Korean Playlist',
    f'감성 플레이리스트 | {title} 🎶',
    f'{title} | 틀어두기 좋은 음악 모음',
]
print(random.choice(formats))
")

DESCRIPTION=$(python3 -c "
import json
with open('$STATE_FILE') as f: d=json.load(f)
title = d.get('selectedPrompt',{}).get('title','')
top = d.get('topTitles',[])
related = '\n'.join([f'· {t}' for t in top[:3]])
print(f'''감성적인 음악 모음 🎵

{related}

📌 구독하고 매주 새로운 플레이리스트를 받아보세요
🔔 알림 설정 ON

#플레이리스트 #감성음악 #KoreanPlaylist #ChillMusic #음악모음''')
")

TAGS="플레이리스트,감성음악,Korean playlist,chill,음악모음,playlist,감성,팝송"

log "제목: $UPLOAD_TITLE"
log "파일: $VIDEO_PATH"

# 채널 키 매핑
case "$CHANNEL" in
  "DGM") CHANNEL_KEY="DGM" ;;
  *) CHANNEL_KEY="DGM" ;;
esac

# 업로드 API 호출
UPLOAD_BODY=$(python3 -c "
import json
body = {
    'action': 'upload',
    'channelKey': '$CHANNEL_KEY',
    'videoPath': '$VIDEO_PATH',
    'title': '$UPLOAD_TITLE',
    'description': '''$DESCRIPTION''',
    'tags': '$TAGS'.split(','),
    'privacyStatus': 'private',
    'madeForKids': False
}
print(json.dumps(body, ensure_ascii=False))
")

log "업로드 중..."
RESULT=$(curl -s -X POST "$API_BASE/api/youtube-upload" \
  -H "Content-Type: application/json" \
  -d "$UPLOAD_BODY")

VIDEO_ID=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('videoId',''))" 2>/dev/null)
SUCCESS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('success',False))" 2>/dev/null)

if [ "$SUCCESS" = "True" ] && [ -n "$VIDEO_ID" ]; then
  YT_URL="https://www.youtube.com/watch?v=$VIDEO_ID"
  log "✅ 업로드 완료!"
  log "📺 URL: $YT_URL"

  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['upload'] = 'done'
d['status'] = 'completed'
d['uploadedVideoId'] = '$VIDEO_ID'
d['uploadedUrl'] = '$YT_URL'
d['uploadTitle'] = '$UPLOAD_TITLE'
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"

  # 완료 리포트 출력
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🎉 DGM Playlist 자동화 완료!"
  echo "채널: $CHANNEL"
  echo "제목: $UPLOAD_TITLE"
  echo "URL:  $YT_URL"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

else
  log "❌ 업로드 실패: $RESULT"
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['upload']='error'
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
"
  exit 1
fi
