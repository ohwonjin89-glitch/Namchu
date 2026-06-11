#!/bin/bash
# 음악 생성 에이전트
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"

log() { echo "[MUSIC][$(date '+%H:%M:%S')] $1"; }

log "음악 생성 시작..."

# 프롬프트 읽기
PROMPT_JSON=$(python3 -c "
import json
with open('$STATE_FILE') as f: d=json.load(f)
p = d.get('selectedPrompt', {})
print(json.dumps(p, ensure_ascii=False))
")

TITLE=$(echo "$PROMPT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('title','감성 플레이리스트'))")
STYLE=$(echo "$PROMPT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('style','Korean chill pop'))")
LYRICS=$(echo "$PROMPT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('lyrics','[Instrumental]'))")

log "제목: $TITLE"
log "스타일: $STYLE"

# Suno API로 음악 생성
GEN_BODY=$(python3 -c "
import json
body = {
    'prompt': '$LYRICS',
    'tags': '$STYLE',
    'title': '$TITLE',
    'make_instrumental': True,
    'wait_audio': False
}
print(json.dumps(body))
")

log "Suno API 요청 중..."
RESULT=$(curl -s -X POST "$API_BASE/api/custom_generate" \
  -H "Content-Type: application/json" \
  -d "$GEN_BODY")

# ID 추출
SONG_IDS=$(echo "$RESULT" | python3 -c "
import json,sys
items = json.load(sys.stdin)
if isinstance(items, list):
    ids = [item.get('id','') for item in items if item.get('id')]
    print(','.join(ids))
" 2>/dev/null)

if [ -z "$SONG_IDS" ]; then
  log "❌ 음악 생성 요청 실패: $RESULT"
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['music']='error'
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
"
  exit 1
fi

log "생성 ID: $SONG_IDS"
log "완료 대기 중 (최대 10분)..."

# 완료 폴링 (최대 10분)
MAX_WAIT=600
ELAPSED=0
AUDIO_URL=""
while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep 15
  ELAPSED=$((ELAPSED+15))

  STATUS=$(curl -s "$API_BASE/api/get?ids=$SONG_IDS")
  AUDIO_URL=$(echo "$STATUS" | python3 -c "
import json,sys
items = json.load(sys.stdin)
if isinstance(items, list) and items:
    item = items[0]
    status = item.get('status','')
    url = item.get('audio_url','')
    if status in ('complete','streaming') and url:
        print(url)
" 2>/dev/null)

  if [ -n "$AUDIO_URL" ]; then
    log "✅ 음악 생성 완료 ($ELAPSED초)"
    break
  fi
  log "  대기 중... ($ELAPSED초) status=$(echo "$STATUS" | python3 -c "import json,sys; items=json.load(sys.stdin); print(items[0].get('status','?') if isinstance(items,list) and items else '?')" 2>/dev/null)"
done

if [ -z "$AUDIO_URL" ]; then
  log "❌ 타임아웃"
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['music']='error'
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
"
  exit 1
fi

# 파일 다운로드
DATE=$(date +%Y%m%d_%H%M%S)
SAVE_DIR="/mnt/c/Users/오원진/AppData/Local/dgm_output/${CHANNEL}/${DATE}"
mkdir -p "$SAVE_DIR"

log "음악 다운로드 중..."
DL_RESULT=$(curl -s -X POST "$API_BASE/api/download" \
  -H "Content-Type: application/json" \
  -d "{\"audioUrl\":\"$AUDIO_URL\",\"fileName\":\"music.mp3\",\"savePath\":\"C:/Users/오원진/AppData/Local/dgm_output/$CHANNEL/$DATE\"}")

LOCAL_PATH="/mnt/c/Users/오원진/AppData/Local/dgm_output/${CHANNEL}/${DATE}/music.mp3"
WIN_PATH="C:\\Users\\오원진\\AppData\\Local\\dgm_output\\${CHANNEL}\\${DATE}\\music.mp3"

# 상태 업데이트
python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['music'] = 'done'
d['musicFile'] = '$WIN_PATH'
d['musicFileLinux'] = '$LOCAL_PATH'
d['outputDir'] = 'C:/Users/오원진/AppData/Local/dgm_output/$CHANNEL/$DATE'
d['outputDirLinux'] = '/mnt/c/Users/오원진/AppData/Local/dgm_output/$CHANNEL/$DATE'
d['songIds'] = '$SONG_IDS'.split(',')
d['audioUrl'] = '$AUDIO_URL'
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"
log "✅ 음악 저장 완료: $LOCAL_PATH"
