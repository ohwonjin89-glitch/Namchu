---
name: dgm-genre-reference
description: DGM 채널의 9개 음악 장르(Lo-fi Focus & Cafe Chill, Groove Hip-hop & Chill Pop, Late Night R&B & Soul, Upbeat City Pop & Funk Groove, Acoustic Indie Pop & Folk Soul, Chillwave & Synth Pop, Jazz-hop & Bossa Nova Chill, Jazz Instrumental/로파이재즈, Old Jazz/올드재즈)에 대한 단일 진실 공급원 — 무드→장르 매핑, 장르→이미지 레퍼런스 폴더 매핑, 채널 선호 우선순위, 테마별 imageKeywords. music-generator/image-generator/strategist가 각자 장르 관련 판단을 할 때 공통으로 참조해 3곳의 테이블이 서로 어긋나는 것을 방지한다.
---

# DGM 장르 레퍼런스

music-generator.md(무드→장르), image-generator.md(장르→레퍼런스 폴더), strategist.md(장르 우선순위, 테마→imageKeywords)에 각각 존재하던 장르 관련 테이블을 여기 하나로 모았다. 세 에이전트는 자기 지침서에 있던 표 대신 이 스킬을 참조하고, 표가 갱신될 때도 여기 한 곳만 고치면 된다.

> ⛔ **단일 장르 원칙**: 한 프로젝트(15회 호출, 30곡)는 주장르 1개만 사용한다. 여러 장르를 블렌딩하거나 트랙마다 다른 장르를 배정하지 않는다 — variation 트랙도 동일 장르 내에서 템포/악기/보컬 뉘앙스만 바꾼다.

## 9개 장르 마스터 테이블

| 장르 | 무드 키워드 (한국어, music-generator 판단 기준) | 이미지 레퍼런스 1순위 폴더 | 이미지 레퍼런스 2순위 폴더 | scene-prompts 섹션 |
|---|---|---|---|---|
| Lo-fi Focus & Cafe Chill | 집중, 카페, 공부, 조용한 배경음악, 로파이 감성 | 카페 | 공부 | 카페 / 공부 |
| Groove Hip-hop & Chill Pop | 도시, 세련됨, 미드템포, NYC 감성, 여유 있는 리듬 | Groove hiphop | 도시배경 | Groove Hiphop / 도시배경 |
| Late Night R&B & Soul | 늦은 밤, 이별, 감성, 드라이브, 로맨틱 | 감성R&B | 도시야경 | 하이틴 / 도시야경 |
| Upbeat City Pop & Funk Groove | 밝은 에너지, 설렘, 여름, 댄서블, 긍정, 도시 활기 | 도시배경 (sref 없음, 일러스트) | 도시야경 (sref 없음, 일러스트) | 시티팝 |
| Acoustic Indie Pop & Folk Soul | 따뜻함, 자연, 위로, 아침 산책, 희망, 어쿠스틱 | 어쿠스틱팝 | 하늘 | 어쿠스틱팝 / 하늘 |
| Chillwave & Synth Pop | 몽환적, 80년대 감성, 드라이브, 신스팝, 하이레조 | 도시야경 | 드라이브 | 도시야경 / 드라이브 |
| Jazz-hop & Bossa Nova Chill | 카페, 여유로운 오후, 대화, 재즈, 보사노바, 소박한 행복 | 카페 | 감성R&B | 카페 / 하이틴 |
| Jazz Instrumental (로파이재즈) | 순수 연주, 가사 없음, 재즈 피아노 트리오, 쿨재즈, 보사노바 | — (instrumental, 이미지는 위 장르 준하는 무드로 별도 판단) | — | — |
| Old Jazz (올드재즈) | 빈티지, 올드재즈, 스윙, 축음기 감성, 클래식 재즈보컬, 1940~1950년대 무드 | 없음 (sref 없음, 텍스트 프롬프트 전용) | — | 올드재즈 |

> `Jazz Instrumental`(사용자 호칭: 로파이재즈)은 `instrumental: true` 필수, `negative_tags`에 `"vocals, singing, lyrics, humming"` 추가. `gemini_analyzer.py`의 `EXISTING_GENRES`/`INSTRUMENTAL_GENRES`에 등록되어 있고, `music-generator-genre-samples.md` 4-8 섹션에 Gemini로 분석한 user_curated 레퍼런스가 있다. `qa-inspector.md`가 이 장르에 한해 "가사/보컬 감지 시 오류곡" 반대 판정을 적용해, 최종 셋에 보컬 트랙이 섞이지 않도록 게이트한다.

> `Old Jazz`(2026-07-26 추가)는 `.claude/agents/reference/`에 아직 전용 사진 레퍼런스 폴더가 없다 — 기존 8개 장르의 어떤 폴더도 빈티지/올드재즈 무드와 맞지 않아, City Pop과 동일한 방식(sref 없이 텍스트 프롬프트만)을 채택한다. `music-generator-genre-samples.md` 4-9 섹션에 Gemini로 분석한 user_curated 레퍼런스 20곡이 있다(`gemini_analyzer.py`의 `EXISTING_GENRES`에 등록됨, `/api/generate-prompts`의 `GENRE_META`/`SECTION_MAP`에도 반영됨). 보컬/인스트루멘탈이 곡마다 섞여 있어 `INSTRUMENTAL_GENRES`에는 포함하지 않음.

### 특수 규칙

- **감성R&B 폴더 → scene 섹션은 "하이틴"을 사용한다** (하이틴 섹션이 emotional R&B 무드를 다룸, 폴더명과 섹션명이 일치하지 않는 유일한 예외).
- **City Pop은 폴더(도시배경/도시야경)와 무관하게 scene-prompts 섹션은 항상 "시티팝"을 사용한다.** 시티팝 섹션은 sref 없이 텍스트 프롬프트만으로 생성하므로 레퍼런스 이미지 선택·base64 인코딩·사본 저장 단계를 전부 생략하고 바로 프롬프트 생성 단계로 진행한다. (야간 테마면 도시야경 폴더, 해안/여름 테마면 도시배경 폴더 쪽 방향성을 참고만 하되 실제 이미지는 실사 레퍼런스를 사용하지 않는다 — 80년대 일러스트 포스터 스타일 전용.)
- **Old Jazz도 City Pop과 동일하게 sref 없이 텍스트 프롬프트만 사용한다** — 레퍼런스 이미지 선택·base64 인코딩·사본 저장 단계를 생략하고 바로 프롬프트 생성 단계로 진행. 방향성은 빈티지 축음기/바이닐, 세피아·앰버 톤, 1950년대 재즈클럽 분위기(실사보다는 따뜻한 일러스트/필름 그레인 질감 권장).
- **Old Jazz는 매 트랙마다 Styles(음악 스타일 프롬프트)에 LP 레코드/바이닐 질감이 반드시 드러나야 한다** (2026-07-26, 사용자 피드백 — 발랄한 톤/촌스러운 아웃트로 문구 등 무드 이탈 오류가 반복 발견됨). `music-generator-genre-samples.md` 4-9 레퍼런스는 20곡 중 일부만 "vinyl crackle"/"vintage vinyl warmth" 표현을 명시하므로, 레퍼런스 원문 그대로 재사용하는 기본 모드에서 선택된 레퍼런스에 vinyl/LP record 관련 질감 표현이 없으면 music-generator가 Styles 끝에 짧은 질감 문구(예: "with a warm vinyl crackle and gentle surface noise texture")를 자연스럽게 덧붙인다. [[suno-style-synthesis]] 합성 모드에서도 `GENRE_META["Old Jazz"].keywords`에 "LP 레코드/바이닐 크랙클 질감"이 포함되어 있어 AI가 매번 반영한다.
- **Old Jazz는 발랄하고 경쾌한 톤을 지양하고 묵직하고 진중한(heavy, somber) 톤을 기본으로 한다** (2026-07-26, 사용자 피드백 — 프로젝트 2026072601의 10/25번곡이 "너무 발랄한 분위기"라 주제/톤 불일치로 삭제됨). 긍정 예시: 같은 프로젝트의 "Last Call Blues"(느린 템포, walking upright bass, muted trumpet, 회고적 무드)가 적합도가 매우 높은 것으로 확인됨 — 레퍼런스 선택 시 이런 느리고 무게감 있는 톤을 우선하고, upbeat/cheerful/bouncy 뉘앙스가 강한 레퍼런스는 anchor로 쓰지 않는다. `GENRE_META["Old Jazz"].negTags`에도 "upbeat cheerful bouncy energy, bright pop energy"가 추가되어 있다.
- **Old Jazz 로파이/축음기 질감은 "은은하게"가 아니라 "또렷하게 들릴 정도"로 강하게 넣는다** (2026-07-27, 사용자 피드백 — 묵직한 톤 테스트 3곡 청취 후 "로파이 느낌이 강하게 나오도록"으로 상향 요청). Styles 문장에 vinyl crackle/surface noise를 언급만 하는 수준이 아니라, 곡 전체에 걸쳐 지속적으로 들리는 축음기 서피스 노이즈 레이어로 명시한다 (예: "a continuous, clearly audible vinyl surface noise and gramophone crackle layered under the entire mix, like an old 78rpm record"). `GENRE_META["Old Jazz"].keywords`/`negTags`도 이에 맞춰 상향(2026-07-27) — `negTags`에 "clean pristine studio mix, digital clarity" 추가로 지나치게 깨끗한 믹스를 배제한다.
- **Old Jazz 보컬 캐스팅: 프로젝트(15회 호출/30곡) 기준 50%는 기존 "묵직한 톤"(굵고 걸걸한 저음 남성 보컬, Louis Armstrong 스타일 참조하되 이름 언급 금지)을 유지하고, 나머지 50%는 남녀 보컬을 랜덤하게 섞는다** (2026-07-27, 사용자 피드백). 이는 [[suno-prompt-authoring]] §7의 장르 전반 50:50 성비 원칙과 별개로, Old Jazz 한정으로 "무거운 앵커 보컬 50% + 나머지 50% 내에서 랜덤 성별" 2단 구조를 적용하라는 지시다 — 즉 전체로 보면 남성 비중이 50%보다 높아질 수 있고, 이는 Old Jazz에 한해 의도된 것이다.
- **"Whiskey-Worn Voice" 테스트 트랙의 스타일/프롬프트 접근은 이후 생성에서 제외한다** (2026-07-27, 사용자 피드백 — "whiskey_worn_voice는 별로야 이 프롬프트는 제외해줘"). 해당 트랙은 `C:\temp_dgm_upload\old_jazz_heavy_test\whiskey_worn_voice_*.mp3`로, 술에 전 목소리(whiskey-worn) 컨셉의 걸걸한 보컬 묘사 방식이었다 — 같은 문구/컨셉을 negative 예시로 취급하고 재사용하지 않는다. "Gravel and Gaslight"/"Smoke Ring Serenade" 방향은 유지.
- **Old Jazz 시대 배경은 1950년대 단독이 아니라 1940~1950년대로 확장한다** (2026-07-27, 사용자 피드백). Styles/컨셉 문구에서 "1950s"만 쓰지 말고 "1940s-1950s"로 표기.

## 채널 선호 장르 우선순위 (strategist 전용)

컨셉이 복수 장르로 해석될 때 아래 순서로 우선 결정한다:

| 우선순위 | 장르 | 적합 컨셉 예시 |
|:---:|---|---|
| ★★★ | Groove Hip-hop & Chill Pop | 도시, 드라이브, 세련된 감성, 미드템포 |
| ★★☆ | Chillwave & Synth Pop | 몽환, 80s 감성, 야경, 신스 분위기 |
| ★☆☆ | Acoustic Indie Pop & Folk Soul | 자연, 위로, 아침, 따뜻한 어쿠스틱 |

위 3개 장르에 해당하지 않는 컨셉은 나머지 장르(Lo-fi, Late Night R&B, Upbeat City Pop, Jazz-hop, Jazz Instrumental) 중에서 선택한다. 최종 장르 우선순위는 트렌드 분석 결과(researcher 리포트)와 concept_brief를 함께 따른다.

## 레퍼런스 배정 원칙 (music-generator 전용)

`generate-prompts` API(`/api/generate-prompts`, POST)를 호출하면 선택 장르의 레퍼런스를 **중복 없이 랜덤 배정**해서 반환한다 — 레퍼런스 수 이내라면 각 레퍼런스가 최대 1회만 사용되고, 레퍼런스 수를 초과하는 경우에만 랜덤 재사용된다. 에이전트가 직접 레퍼런스를 선택·배정하지 않고 반드시 이 API를 통해 받는다. (레퍼런스 풀 로테이션 세부 알고리즘은 [[suno-prompt-authoring]] 스킬 참고.)

## 테마별 imageKeywords (strategist 전용, `visualDirection`/`imageKeywords` 필드 작성 시 참고)

| 주제 | imageKeywords |
|------|--------------|
| 카페 | cozy cafe aesthetic woman warm light |
| 새벽 감성 | late night city lights solitude moody |
| 드라이브 | night drive highway warm city lights window |
| 모닝커피 | morning coffee window sunlight golden |
| 주말 아침 | sunday morning cozy bedroom soft light |
| 공부/작업 | study desk minimal aesthetic lamp |
| 비 오는 날 | rainy day window cozy indoor moody |
| 힐링 자연 | nature forest peaceful green calm |
| 여행 | travel wanderlust scenic view sky |
| 여름/청량 | summer beach blue sky ocean sunny bright outdoor |
| 봄/꽃 | spring cherry blossom flowers soft pastel daylight |

> ⚠️ 주제 카테고리를 혼합하지 않는다 (예: "드라이브할 때 듣는 시티팝"처럼 활동+장르를 섞으면 검색 노출이 애매해진다) — 장르 중심 또는 활동 중심 중 하나로 명확히 좁힌다.

## 이미지 프롬프트 방향 (image-generator 전용, 미드저니 프롬프트 보조 참고)

| 장르 | 미드저니 프롬프트 방향 |
|------|----------------------|
| 감성 R&B | Soft indoor lighting, warm amber tones, intimate atmosphere |
| 시티팝 | Flat retro illustration poster, 80s Japanese city pop album cover style, warm gradient sunset sky, geometric skyline (실사 아님) |
| chill vibe | Cozy room, dim lamp, vinyl record, relaxed atmosphere |
| 감성 힙합 | Late night cityscape, moody blue tones, reflective urban |
| 그루브 힙합 | Vibrant colors, energetic, street aesthetic, dynamic composition |

## Gemini 스타일 분석 보조 (image-generator 전용)

레퍼런스 선정 전 `style-database.json`에 해당 장르의 분석 결과가 있으면 `image_keywords`/`image_palette`/`image_style`을 보조 참고 정보로 활용한다 (레퍼런스 파일 자체를 자동 변경하지 않음 — 사용자가 직접 관리).

## sref 절대 사용 금지 목록 (컬러톤 위반 이력)

| 파일 경로 | 위반 색상 | 이유 |
|---|---|---|
| `도시야경/다리 야경.png` | purple-mauve 하늘 | Midjourney가 purple/magenta 계열 생성 → 2026071201 사고 |
| `도시야경/강변 야경.png` | golden-hour 오렌지 | orange sunset 톤 → avoidKeywords 위반 → 2026071201 사고 |

위 파일은 어떤 컨셉이든 sref로 절대 사용하지 않는다. 폴더(도시야경/)에서 후보를 고를 때 이 두 파일은 건너뛴다. image-generator와 이 스킬을 참조하는 모든 에이전트에 동일하게 적용된다.
