#!/bin/bash
# 트렌드 분석 에이전트
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"
LOG_DIR="/home/wonjin/agents/logs"

log() { echo "[TREND][$(date '+%H:%M:%S')] $1"; }

update_state() {
  python3 -c "
import json, sys
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['trend']='$1'
if len(sys.argv)>2: d['trendData']=json.loads(sys.argv[2])
with open('$STATE_FILE','w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
" "$1" "$2" 2>/dev/null
}

log "트렌드 분석 시작..."

# YouTube API 키 로드 (대시보드 localStorage 대신 파일에서)
YT_KEY_FILE="/mnt/c/Users/오원진/AppData/Local/dgm_config.json"
if [ -f "$YT_KEY_FILE" ]; then
  YT_KEY=$(python3 -c "import json; print(json.load(open('$YT_KEY_FILE')).get('yt_api_key',''))" 2>/dev/null)
fi

if [ -z "$YT_KEY" ]; then
  log "⚠ YouTube API 키 없음 → n8n 캐시 사용"
  # n8n 캐시에서 로드
  CACHE=$(curl -s "$API_BASE/api/trend-cache")
  EXISTS=$(echo "$CACHE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('exists',False))" 2>/dev/null)
  if [ "$EXISTS" = "True" ]; then
    log "✅ n8n 캐시 로드 성공"
    # 캐시 데이터를 상태 파일에 저장
    echo "$CACHE" | python3 -c "
import json,sys
cache = json.load(sys.stdin)
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['trend'] = 'done'
d['trendVideos'] = cache.get('trendVideos', [])
d['trendKeywords'] = []
# 가장 조회수 높은 영상 기반 주제 선정
videos = cache.get('trendVideos', [])
if videos:
    titles = [v.get('title','') for v in videos[:5]]
    d['selectedTopic'] = titles[0] if titles else ''
    d['topTitles'] = titles
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
print('done')
"
    log "주제 선정 완료"
    exit 0
  fi
  log "❌ n8n 캐시도 없음"
  update_state "error"
  exit 1
fi

# YouTube API 직접 호출
log "YouTube API로 트렌드 분석 중..."
RESULT=$(curl -s -X POST "$API_BASE/api/youtube-trends" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"fetch_trends\",\"apiKey\":\"$YT_KEY\",\"days\":7,\"minSubs\":5000}")

SUCCESS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('success',False))" 2>/dev/null)

if [ "$SUCCESS" = "True" ]; then
  echo "$RESULT" | python3 -c "
import json,sys
result = json.load(sys.stdin)
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['trend'] = 'done'
d['trendVideos'] = result.get('videos', [])
d['trendKeywords'] = result.get('keywords', [])
videos = result.get('videos', [])
if videos:
    d['selectedTopic'] = videos[0].get('title', '')
    d['topTitles'] = [v.get('title','') for v in videos[:5]]
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"
  log "✅ 트렌드 분석 완료 ($(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('videos',[])))" 2>/dev/null)개 영상)"
else
  log "❌ 트렌드 분석 실패: $RESULT"
  update_state "error"
  exit 1
fi
