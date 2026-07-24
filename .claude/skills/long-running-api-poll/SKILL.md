---
name: long-running-api-poll
description: 장시간 실행되는 DGM API(Suno 생성 완료 대기, /api/make-video 인코딩, /api/youtube-upload 업로드)를 폴링하는 공용 Bash 패턴 — 하나의 Bash 호출 안에 sleep 루프를 묶어 프롬프트 캐시 TTL(5분)이 깨지지 않게 한다. music-generator, video-producer, youtube-uploader가 동일하게 사용한다.
---

# 장시간 API 폴링 패턴

Suno 생성 완료 대기, 영상 인코딩(`/api/make-video`), YouTube 업로드(`/api/youtube-upload`)는 모두 즉시 끝나지 않는 비동기 작업이다. 세 에이전트 모두 결과를 확인하려면 폴링이 필요한데, **턴(Bash 호출) 하나가 끝나고 다음 턴이 시작되기까지 5분이 넘어가면 프롬프트 캐시가 깨져서 에이전트 지침 전체가 매번 풀가격으로 재처리된다.** 그래서 짧은 간격으로 개별 확인을 반복하지 않고, 하나의 Bash 호출 안에서 sleep 루프로 묶어 최대한 오래 붙잡아둔다.

## 핵심 원칙

- **폴링은 반드시 하나의 Bash 호출 안에서 sleep 루프로 실행한다.** 매번 새 Bash 호출로 한 번씩만 확인하지 않는다.
- Bash 도구 자체의 타임아웃 한도(~10분)가 있으므로, 한 번의 루프는 `seq 1 58` × `sleep 10` ≈ 9분 40초 정도로 설계한다.
- 완료(`done`) 또는 실패(`error`) 상태가 아니면, **동일한 블록을 그대로 다시 호출**해서 다음 ~10분을 이어 폴링한다 (내용을 바꾸지 않고 반복 호출하는 것 자체가 프롬프트 캐시를 유지하는 핵심이다).
- 백그라운드로 던져놓고(`nohup`/`disown`) 나중에 결과만 확인하는 방식은 금지 — orchestrator.md의 하드 룰(무중단워처 금지)과 동일한 이유로, 감시되지 않는 백그라운드 폴링이 중복 업로드 등 사고를 일으킨 전례가 있다.

## 공용 템플릿

```bash
ENCODED_ID=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''{id_or_taskId}'''))")

# 한 번의 Bash 호출 안에서 최대 ~10분 동안 폴링.
# done/error가 아니면 이 블록 전체를 그대로 다시 호출해서 다음 ~10분을 이어 폴링한다.
for i in $(seq 1 58); do
  RESULT=$(curl -s "http://localhost:3000/{ENDPOINT}?{ID_PARAM}=$ENCODED_ID")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
  if [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ]; then
    echo "$RESULT"
    break
  fi
  sleep 10
done
```

## 엔드포인트별 파라미터

| 에이전트 | 엔드포인트 | ID 파라미터 | 완료 상태값 |
|---|---|---|---|
| music-generator | `/api/get` | `ids` (콤마로 여러 개 동시 폴링 가능) | 각 트랙의 상태가 `complete`/`error` |
| video-producer | `/api/make-video` | `taskId` | `status: "done"` / `"error"` |
| youtube-uploader | `/api/youtube-upload` | `taskId` | `status: "done"` / `"error"` |

- music-generator는 여러 트랙을 한 번에 폴링하므로 `ids`에 콤마로 join한 전체 ID 목록을 넣고, 응답에서 트랙별 상태를 개별 확인한다 (단일 `status` 필드가 아님 — `/api/get` 응답 스펙은 api-reference.md 참고).
- youtube-uploader는 POST 응답이 `{"status":"running","taskId":...}` 형태로 즉시 오는 비동기 API다. 이를 실패로 오인해서 같은 요청을 재시도하면 중복 업로드 사고가 난다 (2026062802 인시던트) — 반드시 이 폴링 루프로 완료를 기다리고, `error` 상태가 나와도 같은 `taskId`로 재시도하지 않는다.

## 429 등 레이트리밋 대응

동시 폴링 대상이 많을 때(예: music-generator의 배치 생성) 429가 보이면 폴링 자체의 간격(`sleep 10`)을 늘리기보다, 생성 요청 쪽의 동시 요청 수(BATCH_SIZE)를 줄이는 것이 우선이다 — 폴링은 읽기 전용 GET이라 레이트리밋 원인이 되는 경우는 드물다.
