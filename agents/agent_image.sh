#!/bin/bash
# 이미지 생성 에이전트 (Nano Banana 2 사용)
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"

log() { echo "[IMAGE][$(date '+%H:%M:%S')] $1"; }

log "이미지 생성 시작..."

# 상태에서 정보 읽기
python3 -c "
import json
with open('$STATE_FILE') as f: d=json.load(f)
p = d.get('selectedPrompt', {})
print(p.get('title','감성 플레이리스트'))
print(p.get('style','Korean chill pop'))
" | read -r TITLE; read -r STYLE

TITLE=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('selectedPrompt',{}).get('title','감성 플레이리스트'))")
OUTPUT_DIR=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('outputDirLinux',''))")

# NB2 이미지 프롬프트 생성
NB2_PROMPT="Cinematic Korean playlist album cover, $TITLE, moody atmospheric lighting, soft bokeh, elegant typography, 16:9, high quality digital art"

log "프롬프트: $NB2_PROMPT"
log "Nano Banana 2 요청 중..."

NB2_RESULT=$(curl -s -X POST "$API_BASE/api/nano-banana" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"$NB2_PROMPT\",\"size\":\"1792x1024\",\"quality\":\"hd\"}")

TASK_ID=$(echo "$NB2_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('taskId',''))" 2>/dev/null)
IMAGE_URL=$(echo "$NB2_RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('imageUrl',''))" 2>/dev/null)

# taskId 방식 (비동기)
if [ -n "$TASK_ID" ] && [ -z "$IMAGE_URL" ]; then
  log "비동기 처리 중 (taskId: $TASK_ID)..."
  MAX_WAIT=300
  ELAPSED=0
  while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 10
    ELAPSED=$((ELAPSED+10))
    POLL=$(curl -s "$API_BASE/api/nano-banana?taskId=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TASK_ID'))")")
    STATUS=$(echo "$POLL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
    IMAGE_URL=$(echo "$POLL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('imageUrl',''))" 2>/dev/null)
    if [ "$STATUS" = "done" ] && [ -n "$IMAGE_URL" ]; then
      log "✅ 이미지 생성 완료 ($ELAPSED초)"
      break
    fi
    log "  대기 중... ($ELAPSED초)"
  done
fi

if [ -z "$IMAGE_URL" ]; then
  log "❌ 이미지 생성 실패 — 기본 배경 사용"
  # 폴백: 단색 배경 이미지 생성
  python3 -c "
from PIL import Image, ImageDraw, ImageFont
import os
img = Image.new('RGB', (1920,1080), color=(20,20,30))
img.save('$OUTPUT_DIR/background.jpg', quality=95)
print('기본 배경 생성')
" 2>/dev/null || true
  IMAGE_URL="fallback"
  BG_PATH="$OUTPUT_DIR/background.jpg"
else
  # 이미지 다운로드
  BG_PATH="$OUTPUT_DIR/background.jpg"
  curl -s -L "$IMAGE_URL" -o "$BG_PATH"
  log "이미지 저장: $BG_PATH"
fi

WIN_BG_PATH=$(echo "$BG_PATH" | sed 's|/mnt/c/|C:/|' | sed 's|/|\\|g')

python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['image'] = 'done'
d['bgImageUrl'] = '$IMAGE_URL'
d['bgImagePath'] = '$WIN_BG_PATH'
d['bgImageLinux'] = '$BG_PATH'
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"
log "✅ 이미지 에이전트 완료"
