---
name: suno-style-synthesis
description: 장르 레퍼런스 Styles 여러 개를 AI가 학습해 매번 새로운 오리지널 Styles 프롬프트를 합성 생성하는 방법 — 2026-08-01부터 이것이 기본 동작이다. 레퍼런스 원문을 그대로 재사용하려면(styleMode:"reference") 사용자가 명시적으로 요청해야 한다.
---

# Suno 스타일 합성 생성

## 언제 쓰는가

**기본값은 항상 "레퍼런스를 참고해서 AI가 새로 창작"이다** (2026-08-01부터, `styleMode` 미지정 = `"synthesize"`). 사용자가 아무 말도 하지 않아도 `music-generator`는 `/api/generate-prompts`가 곡마다 배정한 레퍼런스를 학습 예시 삼아 매번 새로운 Styles 프로즈를 합성해서 쓴다.

**레퍼런스 원문을 그대로 재사용**(구 기본값)하려면 사용자/오케스트레이터가 아래처럼 **명시적으로 요청했을 때만** API 호출 시 `styleMode: "reference"`를 지정한다:
- "레퍼런스 그대로 써줘"
- "원문 그대로 사용해줘"
- "새로 만들지 말고 기존 스타일 그대로"

## 왜 기본값이 되었는가

원래 기본값("reference" 모드, 레퍼런스 Styles 문장을 원문 그대로 로테이션)은 레퍼런스 자체가 바뀌지 않으므로, 같은 레퍼런스가 재사용될 때마다(특히 레퍼런스 수보다 요청 곡 수가 많을 때) 사실상 동일한 스타일의 음악이 반복 생성됐다. 실제로 2026-07-30 프로젝트 2026072901에서 레퍼런스 10개짜리 장르에 15곡을 요청해 5쌍이 Styles까지 완전히 동일하게 나왔고, 사용자가 "노래가 전부 비슷하다(도입부/끝나는 부분 리듬·스타일 동일)"고 지적해 프로젝트를 폐기했다([[project-2026072901-styles-duplication-fix]]). 이후 사용자가 "생성요청 시 기본 구조는 레퍼런스 스타일을 참고해서 클로드가 창작하는 구조로, 등록된 레퍼런스를 모두 골고루 사용하고, 곡 구조가 전부 동일하면 안 된다"고 명시적으로 지시해(2026-08-01) 이 스킬의 동작을 기본값으로 전환했다.

이 스킬은 레퍼런스를 "정답(복사 대상)"이 아니라 "학습 예시"로 취급해, 장르의 특징(악기 구성, 템포대, 보컬 톤, 믹스 질감 등)은 유지하면서도 매번 문장 자체는 새로 합성해 다양성을 확보한다.

## 적용 대상

9개 장르 전체에 동일하게 적용된다 (Lo-fi Focus & Cafe Chill, Groove Hip-hop & Chill Pop, Late Night R&B & Soul, Upbeat City Pop & Funk Groove, Acoustic Indie Pop & Folk Soul, Chillwave & Synth Pop, Jazz-hop & Bossa Nova Chill, Jazz Instrumental, Old Jazz) — 장르별 특수 처리는 필요 없다. `Jazz Instrumental`/`Old Jazz`의 경우도 동일한 합성 로직이 그대로 적용되고, `instrumental: true`인 `Jazz Instrumental`은 Suno 섹션 구조([Intro]~[Outro] 7개 태그)만 별도 규칙([[suno-prompt-authoring]] §8)을 따른다.

## 어떻게 동작하는가 (기본값, 아무것도 지정하지 않아도 이렇게 동작)

```json
{
  "selectedGenre": "Groove Hip-hop & Chill Pop",
  "songCount": 15,
  "projectTopic": "...",
  "instrumental": false
}
```

내부 동작:
1. API가 레퍼런스 풀을 **라운드 단위로 재셔플하며** 곡마다 1개씩 "주 레퍼런스"로 배정한다 — 한 라운드(=풀 크기만큼) 안에서는 절대 중복 없이 풀 전체가 균등하게 순환하고, 요청 곡 수가 풀을 초과해 다음 라운드로 넘어갈 때만 이전 레퍼런스가 다시 배정된다. 이 배정은 에이전트가 아니라 API가 전담한다 ([[dgm-genre-reference]] "레퍼런스 배정 원칙" 참고).
2. 곡마다 자신에게 배정된 주 레퍼런스에 더해, 장르 전체에서 무작위로 뽑은 최대 5개 예시를 추가로 함께 제시받는다 — 두 단계(개별 배정 + 장르 전반 예시)로 "레퍼런스가 골고루 쓰인다"는 것과 "장르 특성에서 벗어나지 않는다"는 것을 동시에 만족시킨다.
3. Claude는 이 예시들의 공통 요소(악기 구성, 기타/피아노/신스 역할, 베이스 특징, 드럼 패턴, 보컬 톤, 편곡 흐름, 코러스 특징, 템포대, 조성 힌트, 믹스 질감)를 학습하되, **어떤 예시 문장도 그대로 베끼지 않고** 곡마다 새로운 조합으로 Styles 프로즈를 새로 쓴다 — 그 결과 같은 배치 안에서도 곡마다 인트로/아웃로 리듬과 악기 구성이 달라진다.
4. 응답의 각 곡 객체에 `style`(새로 합성된 문장)과 `styleMode: "synthesize"`가 포함되어 돌아온다. 이 값을 `track_plan.json`의 `tags` 필드에 그대로 사용한다.
5. `negative_tags`는 기존과 동일하게 장르별 고정값(`GENRE_META[genre].negTags`)을 그대로 쓴다 — 합성 대상이 아니다.

## 품질 기준 (반드시 지켜지는지 확인)

합성된 `style` 값은 [[suno-prompt-authoring]] §2의 Styles 작성 기준을 그대로 만족해야 한다:
- 프로즈(완전한 문장) — 키워드 나열 금지
- 부정적 표현은 절대 포함하지 않음 (부정 방향은 `negative_tags`로만 분리)
- 장르에 낯선 악기/톤을 임의로 끌어오지 않음 — 학습한 예시들의 특징 범위 안에서만 변주
- **같은 프로젝트 안에서 두 곡의 Styles가 겹치거나 거의 같으면 안 된다** — 곡마다 다른 조합(악기 페어링, BPM 미세 변화, 믹스 질감)으로 실제 다양성이 생겼는지 확인. 이 기준은 `qa-inspector`의 `duplicate_style` 검사로도 자동 점검된다.

트랙별 anchor/variation 배정([[suno-prompt-authoring]] §5, `styleGroup`)은 합성 모드에서도 동일하게 유지된다 — anchor는 장르 기준에 가장 가깝게, variation은 학습된 범위 안에서 더 크게 변주하도록 자연스럽게 반영된다.

## 레퍼런스 풀 자체는 변경하지 않는다

이 스킬은 **생성 시점에만** 새 Styles를 합성할 뿐, `.claude/agents/music-generator-genre-samples.md`의 레퍼런스 풀이나 `style-database.json`을 수정하지 않는다. 레퍼런스 풀 자체를 추가/교체하려면 기존대로 `python scripts/gemini_analyzer.py add-curated`를 사용한다. 레퍼런스 풀이 프로젝트당 필요 곡 수(15개)보다 적은 장르는 재사용 라운드가 자주 발생하므로, 가능하면 풀을 15개 이상으로 유지한다.
