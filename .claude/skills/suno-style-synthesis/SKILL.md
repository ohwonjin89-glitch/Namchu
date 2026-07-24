---
name: suno-style-synthesis
description: 장르 레퍼런스 Styles 여러 개를 AI가 학습해 매번 새로운 오리지널 Styles 프롬프트를 합성 생성하는 방법 — 사용자가 "새로운 스타일로", "신규 프롬프트 생성해줘" 등을 명시적으로 요청했을 때만 사용한다. 기본값(아무 언급 없을 때)은 기존 레퍼런스 Styles를 그대로 재사용하는 현재 방식이며, 이 스킬은 그 기본값을 바꾸지 않는다.
---

# Suno 스타일 합성 생성

## 언제 쓰는가

**기본값은 항상 "레퍼런스 그대로 재사용"이다.** 사용자가 아무 말도 하지 않으면 `music-generator`는 지금까지와 동일하게 `/api/generate-prompts`가 반환한 레퍼런스 Styles 원문을 그대로 Suno `tags`로 사용한다 ([[suno-prompt-authoring]] §5 그대로 유지).

이 스킬은 사용자가 아래처럼 **명시적으로 요청했을 때만** 적용한다:
- "새로운 스타일로 만들어줘"
- "신규 프롬프트 생성해줘"
- "기존 레퍼런스 말고 AI가 새로 스타일을 만들게 해줘"
- 기타 "다양한/새로운 스타일"을 명확히 원한다는 취지의 요청

## 왜 필요한가

기존 방식은 장르당 최대 20개의 레퍼런스 Styles 문장을 **그대로** 로테이션해서 쓴다 — 레퍼런스 자체는 바뀌지 않으므로, 같은 레퍼런스가 재사용될 때마다(특히 레퍼런스 수보다 요청 곡 수가 많을 때) 사실상 동일한 스타일의 음악이 반복 생성된다. 이 스킬은 레퍼런스를 "정답"이 아니라 "학습 예시"로 취급해, 장르의 특징(악기 구성, 템포대, 보컬 톤, 믹스 질감 등)은 유지하면서도 매번 문장 자체는 새로 합성해 다양성을 높인다.

## 적용 대상

8개 장르 전체에 동일하게 적용된다 (Lo-fi Focus & Cafe Chill, Groove Hip-hop & Chill Pop, Late Night R&B & Soul, Upbeat City Pop & Funk Groove, Acoustic Indie Pop & Folk Soul, Chillwave & Synth Pop, Jazz-hop & Bossa Nova Chill, Jazz Instrumental) — 장르별 특수 처리는 필요 없다. `Jazz Instrumental`의 경우도 동일한 합성 로직이 그대로 적용되고, `instrumental: true`이므로 Suno 섹션 구조([Intro]~[Outro] 7개 태그)만 별도 규칙([[suno-prompt-authoring]] §8)을 따른다.

## 어떻게 동작하는가

`/api/generate-prompts` POST 호출 시 `styleMode: "synthesize"`를 추가하면 된다 (미지정 시 기본값 `"reference"`, 기존 동작과 완전히 동일):

```json
{
  "selectedGenre": "Groove Hip-hop & Chill Pop",
  "songCount": 15,
  "projectTopic": "...",
  "instrumental": false,
  "styleMode": "synthesize"
}
```

내부 동작:
1. API가 해당 장르의 레퍼런스 풀에서 최대 5개를 무작위로 뽑아 "학습용 예시"로 Claude에게 제시한다.
2. Claude는 예시들의 공통 요소(악기 구성, 기타/피아노/신스 역할, 베이스 특징, 드럼 패턴, 보컬 톤, 편곡 흐름, 코러스 특징, 템포대, 조성 힌트, 믹스 질감)를 학습하되, **어떤 예시 문장도 그대로 베끼지 않고** 곡마다 새로운 조합으로 Styles 프로즈를 새로 쓴다.
3. 응답의 각 곡 객체에 `style`(새로 합성된 문장)과 `styleMode: "synthesize"`가 포함되어 돌아온다. 이 값을 `track_plan.json`의 `tags` 필드에 그대로 사용한다.
4. `negative_tags`는 기존과 동일하게 장르별 고정값(`GENRE_META[genre].negTags`)을 그대로 쓴다 — 합성 대상이 아니다.

## 품질 기준 (반드시 지켜지는지 확인)

새로 합성된 `style` 값도 [[suno-prompt-authoring]] §2의 Styles 작성 기준을 그대로 만족해야 한다:
- 프로즈(완전한 문장) — 키워드 나열 금지
- 부정적 표현은 절대 포함하지 않음 (부정 방향은 `negative_tags`로만 분리)
- 장르에 낯선 악기/톤을 임의로 끌어오지 않음 — 학습한 예시들의 특징 범위 안에서만 변주
- 곡마다 다른 조합(악기 페어링, BPM 미세 변화, 믹스 질감)으로 실제 다양성이 생겼는지 확인

트랙별 anchor/variation 배정([[suno-prompt-authoring]] §5, `styleGroup`)은 합성 모드에서도 동일하게 유지된다 — anchor는 장르 기준에 가장 가깝게, variation은 학습된 범위 안에서 더 크게 변주하도록 자연스럽게 반영된다.

## 레퍼런스 풀 자체는 변경하지 않는다

이 스킬은 **생성 시점에만** 새 Styles를 합성할 뿐, `.claude/agents/music-generator-genre-samples.md`의 레퍼런스 풀이나 `style-database.json`을 수정하지 않는다. 레퍼런스 풀 자체를 추가/교체하려면 기존대로 `python scripts/gemini_analyzer.py add-curated`를 사용한다.
