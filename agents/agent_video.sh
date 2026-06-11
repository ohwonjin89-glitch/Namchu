#!/bin/bash
# 영상 제작 에이전트
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"

log() { echo "[VIDEO][$(date '+%H:%M:%S')] $1"; }

log "영상 제작 시작..."

# 상태에서 필요한 정보 읽기
MUSIC_PATH=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('musicFile',''))")
BG_IMAGE=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('bgImagePath',''))")
TITLE=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('selectedPrompt',{}).get('title','감성 플레이리스트'))")
OUTPUT_DIR=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('outputDir',''))")
OUTPUT_DIR_LINUX=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('outputDirLinux',''))")

log "음악: $MUSIC_PATH"
log "배경: $BG_IMAGE"
log "제목: $TITLE"

# 영상 제작 API 호출
VIDEO_BODY=$(python3 -c "
import json
body = {
    'bgImageUrl': '',
    'bgImagePath': '$BG_IMAGE',
    'audioPath': '$MUSIC_PATH',
    'outputDir': '$OUTPUT_DIR',
    'texts': [
        {
            'content': '$TITLE',
            'fontFamily': '맑은 고딕',
            'fontSize': 52,
            'color': '#FFFFFF',
            'leftPct': 5,
            'topPct': 80,
            'widthPct': 90,
            'heightPct': 10,
            'bold': True,
            'shadow': False
        }
    ],
    'spectrum': {
        'enabled': True,
        'color': '#A78BFA',
        'leftPct': 5,
        'topPct': 88,
        'widthPct': 90,
        'heightPct': 8
    },
    'watermark': {
        'enabled': True,
        'text': '@DGM_Playlist',
        'position': 'bottomRight'
    }
}
print(json.dumps(body))
")

log "영상 제작 API 요청..."
RESULT=$(curl -s -X POST "$API_BASE/api/make-video" \
  -H "Content-Type: application/json" \
  -d "$VIDEO_BODY")

TASK_ID=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('taskId',''))" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
  log "❌ 영상 제작 요청 실패: $RESULT"
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['video']='error'
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
"
  exit 1
fi

log "영상 제작 중 (taskId: $TASK_ID)..."

# 완료 폴링 (최대 15분)
MAX_WAIT=900
ELAPSED=0
VIDEO_PATH=""
while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep 10
  ELAPSED=$((ELAPSED+10))

  POLL=$(curl -s "$API_BASE/api/make-video?taskId=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TASK_ID'))")")
  STATUS=$(echo "$POLL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
  PROGRESS=$(echo "$POLL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('progress',0))" 2>/dev/null)
  VIDEO_PATH=$(echo "$POLL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('outputPath',''))" 2>/dev/null)

  if [ "$STATUS" = "done" ] && [ -n "$VIDEO_PATH" ]; then
    log "✅ 영상 제작 완료 ($ELAPSED초): $VIDEO_PATH"
    break
  fi
  log "  진행 중... ${PROGRESS}% ($ELAPSED초)"
done

if [ -z "$VIDEO_PATH" ]; then
  log "❌ 영상 제작 타임아웃"
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['video']='error'
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
"
  exit 1
fi

python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['video'] = 'done'
d['videoPath'] = '$VIDEO_PATH'
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"
log "✅ 영상 에이전트 완료"
