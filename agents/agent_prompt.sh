#!/bin/bash
# 프롬프트 작성 에이전트
CHANNEL=$1
API_BASE="http://localhost:3000"
STATE_FILE="/tmp/dgm_state_$CHANNEL.json"

log() { echo "[PROMPT][$(date '+%H:%M:%S')] $1"; }

log "프롬프트 작성 시작..."

# 트렌드 데이터 읽기
TOP_TITLES=$(python3 -c "
import json
with open('$STATE_FILE') as f: d=json.load(f)
titles = d.get('topTitles', [])
print('\n'.join(titles[:5]))
" 2>/dev/null)

log "참고 트렌드 제목:"
echo "$TOP_TITLES" | while read line; do log "  - $line"; done

# Claude API로 음악 프롬프트 생성
PROMPT_REQ=$(python3 -c "
import json
with open('$STATE_FILE') as f: d=json.load(f)
titles = d.get('topTitles', [])
keywords = [k.get('word','') for k in d.get('trendKeywords',[])][:10]
req = {
  'channel': '$CHANNEL',
  'trendTitles': titles,
  'trendKeywords': keywords,
  'count': 3
}
print(json.dumps(req, ensure_ascii=False))
")

RESULT=$(curl -s -X POST "$API_BASE/api/generate-prompts" \
  -H "Content-Type: application/json" \
  -d "$PROMPT_REQ")

SUCCESS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print('error' not in d)" 2>/dev/null)

if [ "$SUCCESS" = "True" ]; then
  echo "$RESULT" | python3 -c "
import json,sys
result = json.load(sys.stdin)
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['prompt'] = 'done'
prompts = result.get('prompts', result.get('suggestions', []))
d['musicPrompts'] = prompts
# 첫 번째 프롬프트 선택
if prompts:
    first = prompts[0]
    d['selectedPrompt'] = {
        'title': first.get('title', '감성 플레이리스트'),
        'style': first.get('style', ''),
        'lyrics': first.get('lyrics', '[Instrumental]'),
        'tags': first.get('tags', 'Korean playlist, chill, emotional')
    }
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
print(f\"프롬프트 {len(prompts)}개 생성됨\")
"
  log "✅ 프롬프트 작성 완료"
else
  log "❌ 프롬프트 생성 실패: $RESULT"
  # 폴백: 기본 프롬프트
  python3 -c "
import json
with open('$STATE_FILE','r') as f: d=json.load(f)
d['steps']['prompt'] = 'done'
d['selectedPrompt'] = {
    'title': '감성 한국 플레이리스트',
    'style': 'Korean emotional pop, piano, soft drums, chill',
    'lyrics': '[Verse]\n감성적인 멜로디\n마음을 울리는 음악\n[Chorus]\n플레이리스트\n[Outro]\n[Instrumental]',
    'tags': 'Korean playlist, emotional, chill, pop'
}
d['musicPrompts'] = [d['selectedPrompt']]
with open('$STATE_FILE','w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
"
  log "⚠ 기본 프롬프트로 폴백"
fi
