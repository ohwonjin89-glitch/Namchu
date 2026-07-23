---
name: suno-prompt-authoring
description: Suno AI 커스텀 생성용 Styles/Lyrics 프롬프트 작성 규칙 — 공통 기본값, Styles 문장체 작성법, Lyrics 파트태그/금지어/주제어 회피, 장르별 레퍼런스 로테이션, 보컬(여성/남성) 스타일 기준, instrumental 모드 템플릿, 최종 검수 체크리스트. music-generator 에이전트가 트랙별 프롬프트를 만들 때마다 참조한다.
---

# Suno 프롬프트 작성

music-generator 에이전트가 `custom_generate` 호출 전 Styles/Lyrics 텍스트를 만들 때 이 스킬을 참조한다. 장르가 정해진 이후, 트랙마다(또는 배치마다) 다시 읽어도 되지만 매 턴 반복해서 읽을 필요는 없다.

## 1. 공통 기본값

모든 트랙에 예외 없이 적용:

```text
- 가사 언어: 영어 (Pop 표준)
- 길이: 약 3분 (150~210초)
- 인트로 3초 안에 강한 인상을 주는 구성
- 의미없는 애드리브 금지: humming, ooh-ooh, la-la, mm-mm 등
- 특정 아티스트를 직접 모방하는 표현 금지 (스타일 유사성은 허용, 이름 언급은 금지)
- 플레이리스트에 자연스럽게 어울리는 톤 (과도하게 튀지 않게)
- SUNO 파트 태그를 명확히 사용 ([Verse], [Chorus] 등)
- concept_brief의 주제 단어를 가사에 직접 언급하지 않는다 (§3 참고)
```

## 2. Styles 작성 기준

**Styles는 반드시 완전한 문장(prose)으로 작성한다 — 키워드 나열 금지.** Suno는 문장 형태의 설명을 키워드 리스트보다 훨씬 잘 반영한다.

포함해야 할 요소:
- 장르 + 서브장르
- 인트로 임팩트 (첫 3초에 무엇이 들리는지)
- 사용 악기
- 기타/피아노/신스의 역할
- 베이스 특징
- 드럼 패턴
- 보컬 톤
- 편곡 흐름 (verse→chorus 전개)
- 코러스 특징
- 템포(BPM 대역) + 박자
- 조성(key) 힌트
- 믹스 질감 (warm/lo-fi/clean/wide 등)

**부정적 방향(넣고 싶지 않은 것)은 절대 `tags`에 쓰지 않는다 — 반드시 `negative_tags` 파라미터로 분리한다.** `tags`에 부정 표현("no drums", "not too fast" 등)을 섞으면 Suno API가 400 에러를 반환한다.

❌ 나쁜 예 (키워드 나열):
```
lofi, chill, piano, rain, jazzy, relaxing, no vocals
```

✅ 좋은 예 (문장체):
```
A warm lo-fi jazz-hop track with a mellow electric piano leading the intro,
soft vinyl crackle texture, a laid-back boom-bap drum pattern around 78 BPM,
a round upright-bass-style bassline, gentle rain ambience woven under the mix,
and a breathy, intimate female vocal that enters after a brief instrumental hook.
```
(그리고 `negative_tags`에 별도로: `"loud drums, aggressive, distortion"`)

## 3. Lyrics 작성 기준

### 3-1. 파트 태그 구조 (고정)

```
[Intro] → [Verse 1] → [Pre-Chorus] → [Chorus] → [Verse 2] → [Pre-Chorus] → [Chorus] → [Bridge] → [Final Chorus] → [Outro]
```

약 3분 곡 기준 섹션별 줄 수 예산(가이드라인, ±1~2줄 허용):
- Intro: 0~2줄 (또는 태그만)
- Verse: 4줄
- Pre-Chorus: 2줄
- Chorus: 4줄
- Bridge: 2~4줄
- Outro: 0~2줄

### 3-2. 금지 단어

다음은 가사에 절대 넣지 않는다: humming, hums, ooh-ooh, whoa-oh, la-la, mm-mm, hmm, 의미없는 애드리브, scat singing.

### 3-3. 주제 단어 직접 언급 금지

concept_brief의 `avoidKeywords`에 있는 단어(및 그 명백한 동의어)를 가사에 절대 직접 쓰지 않는다. 분위기와 감정으로 우회 표현한다.

예시:
- 카페 컨셉 → "cafe", "coffee", "latte", "americano" 등 직접 언급 금지 → 대신 따뜻한 실내, 잔잔한 오후 분위기로 우회
- 드라이브 컨셉 → "drive", "driving", "road trip" 금지 → 대신 움직임과 풍경의 흐름으로 우회
- 야경 컨셉 → "night view", "city lights" 금지 → 대신 빛과 고요함의 정서로 우회

## 4. 장르별 Styles+Lyrics 샘플

`.claude/agents/music-generator-genre-samples.md`를 읽는다 (프로젝트당 장르가 확정된 시점에 1회만 읽으면 되고, 매 턴 다시 읽지 않는다). 장르별 카테고리 및 무드 키워드 매핑은 [[dgm-genre-reference]] 스킬을 참고한다.

## 5. 장르별 레퍼런스 풀 운영 (로테이션)

- 장르당 레퍼런스는 최대 20개: 영구 보호되는 기본 샘플 1개 + 사용자 큐레이션 최대 19개.
- 사용자가 레퍼런스를 추가할 때는 `python scripts/gemini_analyzer.py add-curated` 사용.
- **배치 방식**: 풀 안의 레퍼런스를 한 바퀴 순서대로 소진한 뒤, 그다음부터는 무작위로 재사용한다 (같은 레퍼런스가 연속으로 몰리지 않게).
- **기본값: Styles는 레퍼런스에서 가져온 문장을 거의 그대로 사용**하고, **Lyrics는 항상 새로 쓴다** — 레퍼런스의 가사는 구조(파트 태그 배치)만 참고한다.
- **사용자가 "새로운 스타일로/신규 프롬프트로 생성해줘"라고 명시적으로 요청한 경우에만** [[suno-style-synthesis]] 스킬을 참고해 `/api/generate-prompts` 호출 시 `styleMode: "synthesize"`를 지정한다 — 이때는 Styles도 레퍼런스를 학습 예시 삼아 AI가 매번 새로 합성한다. 아무 언급이 없으면 항상 기본값(레퍼런스 그대로)을 쓴다.
- 레퍼런스 번호 할당은 `/api/generate-prompts` API가 유일한 권한을 가진다. 에이전트가 임의로 레퍼런스 번호를 스스로 부여하지 않는다.
- 풀이 20개를 초과하면, AI가 가장 약한(품질이 낮거나 중복된) 레퍼런스를 골라 제거한다.

## 6. 여성 보컬 스타일 기준

기본 방향: soft, breathy, husky한 저음역, airy falsetto. 백예린 스타일을 참고 지점으로 삼되 이름을 가사나 Styles에 직접 쓰지 않는다.

✅ 좋은 Styles 표현 예:
```
a soft, breathy female vocal with a slightly husky lower register and airy falsetto
accents on the high notes, intimate and close-mic'd
```

❌ 피해야 할 보컬 방향: 벨팅 위주의 파워풀한 창법, 오페라틱한 발성, 과도한 비브라토.

## 7. 남성 보컬 스타일 기준

기본 방향: warm, relaxed, mid-low 음역, 대화하듯 편안한 톤, 가볍고 멜로딕한 랩-싱잉 혼합.

✅ 좋은 Styles 표현 예:
```
a warm, relaxed male vocal in a mid-low register with a conversational delivery,
occasionally blending into light melodic rap-singing during verses
```

**여성 보컬 섹션과 동일한 비중으로 다뤄야 한다** — 여성 보컬 쪽으로 스타일이 쏠리지 않도록 트랙 계획 단계에서 50:50(±15%p) 성비를 명시적으로 배정한다 (아래 §9 및 [[track-block-ordering]] 관련 없음, music-generator 자체 트랙 플랜 로직).

## 8. Instrumental 모드 전용 템플릿

`instrumental: true`인 트랙(예: Jazz Instrumental)은 아래 7섹션 태그 구조를 사용한다 — **섹션 수가 적으면 Suno가 1분 미만의 짧은 곡을 생성하는 경향이 있으므로 반드시 7개 섹션을 채운다**:

```
[Intro] [INSTRUMENTAL] - 1문장 무드 설명
[Section A] [INSTRUMENTAL] - 1문장 무드 설명
[Section B] [INSTRUMENTAL] - 1문장 무드 설명
[Section C] [INSTRUMENTAL] - 1문장 무드 설명
[Bridge] [INSTRUMENTAL] - 1문장 무드 설명
[Section D] [INSTRUMENTAL] - 1문장 무드 설명
[Outro] [INSTRUMENTAL] - 1문장 무드 설명
```

instrumental 모드에서도 금지 단어 목록(§3-2)은 동일하게 적용되며, `negative_tags`에 보컬 관련 방지 태그("vocals, singing, lyrics")를 추가로 넣는다.

## 9. 최종 검수 체크리스트

Styles/Lyrics를 API에 보내기 직전 아래 10개 항목을 확인한다:

1. Styles가 문장체인가 (키워드 나열 아님)
2. 부정적 방향이 `tags`가 아닌 `negative_tags`에 들어있는가
3. Lyrics 파트 태그가 고정 구조를 따르는가
4. 금지 단어(§3-2)가 없는가
5. avoidKeywords 관련 주제 단어가 직접 언급되지 않았는가
6. 특정 아티스트 이름이 직접 언급되지 않았는가
7. 길이가 약 3분 예산에 맞게 설계되었는가
8. 보컬 성별이 트랙 플랜과 일치하는가 (instrumental이면 vocal 관련 태그 전부 제외)
9. 장르가 하나로 명확히 고정되어 있는가 (혼합 금지)
10. 인트로가 3초 안에 인상을 주는 구성인가
