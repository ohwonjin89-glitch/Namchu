# 배경 주제별 미드저니 프롬프트 가이드 (image-generator 참조용)

> image-generator.md Section 4(미드저니 AI 이미지 생성)에서 레퍼런스 폴더의 배경 주제를 정한 뒤, 아래에서 해당 주제 1개 섹션(장면 구성/스타일/금지/템플릿/예시)만 펼쳐서 참고한다. 전체를 매번 다 읽을 필요 없음 — 결정된 주제 1개 섹션만 확인.

> `{referenceDir}`는 실행 환경에 따라 다르다 (이 레퍼런스 이미지들은 저장소에 커밋되어 있어 `git clone`만으로 항상 존재한다):
> - Windows 네이티브: `C:\suno-api\.claude\agents\reference`
> - VPS(Linux, 현재): `/home/dgm/suno-api/.claude/agents/reference`
> - RunPod(Linux, 구): `/workspace/suno-api/.claude/agents/reference`

---

#### 도시배경 전용 프롬프트 기준

선택한 레퍼런스 폴더의 주제가 **도시배경**일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. 도시배경이 아닌 경우에는 추가 운영 지침 1+2의 프롬프트 구성을 따른다.

**레퍼런스는 장면 복제가 아닌 분위기·조명·색감·공기감 참조용으로만 사용한다.**

##### 장면 구성 원칙

Claude는 사용자의 요청 주제에 따라 도시배경 장면을 적절히 변형하여 사용한다.

장면은 레퍼런스와 **다르게** 구성하며, 아래 요소를 새롭게 조합한다:
- 도로 형태 / 건물 배치 / 시점 / 거리 폭
- 가로수 유무 / 차량·보행자 밀도 / 카페·상점·광장 등

예시 장면:
- tree-lined city street
- downtown intersection
- outdoor cafe street
- modern boulevard
- riverside urban walkway
- pedestrian shopping street
- business district street
- quiet residential city road
- urban park edge street
- city square with surrounding buildings

##### 스타일 방향

- natural real-life photo
- casual real-world photography
- natural daylight
- realistic shadows
- slightly imperfect framing
- natural colors
- everyday atmosphere
- mild lens softness
- not overly polished
- not cinematic

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- CGI / obvious AI look / overly perfect composition
- hyperreal look / HDR-heavy rendering / oversaturated colors
- fantasy lighting / glossy surfaces / cartoon / illustration
- text / logo

아래 표현은 가급적 사용하지 않는다:
- cinematic / ultra detailed / hyper detailed / dramatic lighting
- perfect composition / highly stylized / vibrant colors (과도하게)

##### 도시배경 공통 프롬프트 템플릿

```
A natural real-life photo of [scene], inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Casual real-world photography, natural daylight, realistic shadows, slightly imperfect framing, natural colors, everyday atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

`[scene]` 작성 규칙:
1. 도시배경 범위를 벗어나지 않는다
2. 레퍼런스 이미지의 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구도, 다른 위치, 다른 장면이 되도록 설정한다
4. 주제가 구체적일수록 `[scene]`을 구체화하고, 추상적이면 도시배경 안에서 자연스러운 장면을 선택한다

프롬프트 작성 시 아래 개념을 반드시 포함한다:
- mood / lighting / color palette / different composition / different viewpoint / different location

##### 도시배경 프롬프트 예시

```
A natural real-life photo of a tree-lined city street, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Casual real-world photography, natural daylight, realistic shadows, slightly imperfect framing, natural colors, everyday atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

```
A natural real-life photo of a cozy urban cafe street, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Casual real-world photography, natural daylight, realistic shadows, slightly imperfect framing, natural colors, everyday atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

---

#### 도시야경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\도시야경`

선택한 레퍼런스 폴더가 **도시야경** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. (도시야경, 노을 도시, 해질녘 스카이라인, 야간 도시 풍경, 강변 도시 야경, 브릿지 야경, R&B/Chill/City Pop 플레이리스트 도시 배경 주제 포함)

**레퍼런스는 장면 복제가 아닌 노을 색감·도시 조명·스카이라인 밀도·강 반사·필름 질감·저녁 공기감 참조용으로만 사용한다.** 낮 시간의 청량한 도시 거리는 이 섹션이 아닌 **도시배경** 섹션을 적용한다.

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 원칙을 따른다:

- 도시, 다리, 강, 빌딩 배치는 새롭게 만든다 — 레퍼런스와 동일한 도시·랜드마크·다리·구도를 그대로 재현하지 않는다
- 특정 랜드마크는 사용자가 명시적으로 요청한 경우에만 포함하며, 기본적으로 실제 도시명을 프롬프트에 넣지 않는다
- 인물은 넣지 않는다
- 도시 조명은 자연스럽게 켜져 있어야 하며, 과장된 사이버펑크 도시처럼 만들지 않는다
- 하늘은 극적인 판타지 하늘이 아니라 실제 노을과 블루아워 사이의 색감으로 표현한다

예시 장면:
- a wide riverfront skyline at dusk with warm building lights and soft reflections on the water
- a dense downtown skyline under a pink and lavender sunset sky, viewed from a distant rooftop
- a large suspension bridge over dark water with city lights behind it
- a calm blue hour cityscape across the river, with glowing office windows and gentle haze
- a quiet night city skyline with soft haze and distant lights
- a moody metropolitan skyline with a bridge crossing the frame and warm lights reflected in dark water

##### 스타일 방향

- natural real-life cityscape photo
- dusk or blue hour skyline
- warm city lights
- pink, orange, lavender, or purple sunset sky
- dense urban skyline
- bridge lights if appropriate
- river or harbor reflections if appropriate
- soft atmospheric haze
- muted film-like colors
- realistic building lights
- slightly imperfect real-world framing
- calm urban night mood
- playlist background atmosphere
- not overly polished
- not hyperreal
- not CGI

실제 도시 사진처럼 자연스럽고 덜 AI스럽게 보이는 이미지를 목표로 한다.

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- text / logo / watermark / handwritten title / music title / artist name / subtitle
- CGI / obvious AI look / hyperreal rendering / HDR-heavy image
- oversaturated colors / fantasy skyline / futuristic cyberpunk city
- unrealistic building geometry / warped skyscrapers / duplicated landmarks / excessive glow
- cartoon / illustration / 3D render

아래 표현은 가급적 사용하지 않는다:
- ultra detailed / hyper detailed / epic cinematic / dramatic fantasy lighting
- cyberpunk / futuristic city / perfect composition / vibrant oversaturated colors

##### 도시야경 공통 프롬프트 템플릿

```
A natural real-life cityscape photo of [expanded night city scene], inspired only by the mood, lighting, color palette, skyline depth, and evening atmosphere of the reference image, but with a different city layout, different composition, different viewpoint, and different landmark arrangement. Dusk or blue hour skyline, warm building lights, soft pink and lavender evening sky, subtle atmospheric haze, realistic windows, calm river reflections if appropriate, muted film-like colors, slightly imperfect real-world framing, playlist background mood, not overly polished, not hyperreal. --ar 16:9 --style raw --s 20 --v 6 --no text, logo, watermark, handwritten title, music title, artist name, subtitles, CGI, AI look, HDR, oversaturated colors, fantasy skyline, cyberpunk, warped buildings, duplicated landmarks, cartoon, illustration, 3D render
```

##### [expanded night city scene] 작성 규칙

`[expanded night city scene]`는 입력된 주제에 맞게 완성된 영어 장면 문장으로 확장한다.

1. 도시야경 범위를 벗어나지 않는다
2. 레퍼런스 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 도시 배치, 다른 구도, 다른 시점으로 작성한다
4. 한국어 단어를 그대로 넣지 않고 반드시 완성된 영어 장면 문장으로 확장한다

나쁜 예: `city night` / `[도시야경]` / `New York vibe` / `night city background`

좋은 예:
```
a wide riverfront skyline at dusk with a suspension bridge, warm building lights, and soft reflections on the water
a dense downtown skyline under a pink and lavender sunset sky, viewed from a distant rooftop
a calm blue hour cityscape across the river, with glowing office windows and gentle haze
a moody metropolitan skyline with a bridge crossing the frame and warm lights reflected in dark water
```

##### 도시야경 프롬프트 예시

**입력: 도시야경**
```
A natural real-life cityscape photo of a wide riverfront skyline at dusk with warm building lights and soft reflections on the water, inspired only by the mood, lighting, color palette, skyline depth, and evening atmosphere of the reference image, but with a different city layout, different composition, different viewpoint, and different landmark arrangement. Dusk skyline, soft pink and lavender evening sky, subtle atmospheric haze, realistic windows, calm river reflections, muted film-like colors, slightly imperfect real-world framing, playlist background mood, not overly polished, not hyperreal. --ar 16:9 --style raw --s 20 --v 6 --no text, logo, watermark, handwritten title, music title, artist name, subtitles, CGI, AI look, HDR, oversaturated colors, fantasy skyline, cyberpunk, warped buildings, duplicated landmarks, cartoon, illustration, 3D render
```

**입력: 브릿지 야경**
```
A natural real-life cityscape photo of a large suspension bridge crossing over a dark river with a glowing skyline behind it, inspired only by the mood, lighting, color palette, skyline depth, and evening atmosphere of the reference image, but with a different bridge shape, different city layout, different composition, and different viewpoint. Blue hour sky, warm bridge lights, realistic building windows, soft water reflections, muted purple-gray tones, subtle atmospheric haze, slightly imperfect real-world framing, calm playlist background mood, not overly polished, not hyperreal. --ar 16:9 --style raw --s 20 --v 6 --no text, logo, watermark, handwritten title, music title, artist name, subtitles, CGI, AI look, HDR, oversaturated colors, fantasy skyline, cyberpunk, warped buildings, duplicated landmarks, cartoon, illustration, 3D render
```

**입력: 노을 도시**
```
A natural real-life cityscape photo of a dense downtown skyline under a soft pink, orange, and lavender sunset sky, inspired only by the mood, lighting, color palette, skyline depth, and evening atmosphere of the reference image, but with a different city layout, different composition, different viewpoint, and different landmark arrangement. Warm building lights beginning to glow, subtle haze, realistic skyscraper silhouettes, muted film-like colors, calm urban evening mood, slightly imperfect real-world framing, playlist background atmosphere, not overly polished, not hyperreal. --ar 16:9 --style raw --s 20 --v 6 --no text, logo, watermark, handwritten title, music title, artist name, subtitles, CGI, AI look, HDR, oversaturated colors, fantasy skyline, cyberpunk, warped buildings, duplicated landmarks, cartoon, illustration, 3D render
```

**입력: 플레이리스트 배경**
```
A natural real-life cityscape photo of a calm evening skyline with open sky space, warm city lights, and soft river reflections, inspired only by the mood, lighting, color palette, skyline depth, and evening atmosphere of the reference image, but with a different city layout, different composition, different viewpoint, and different landmark arrangement. Dusk or blue hour mood, muted pink and purple sky, realistic buildings, subtle haze, clean open area for playlist visual, film-like colors, slightly imperfect real-world framing, not overly polished, not hyperreal. --ar 16:9 --style raw --s 20 --v 6 --no text, logo, watermark, handwritten title, music title, artist name, subtitles, CGI, AI look, HDR, oversaturated colors, fantasy skyline, cyberpunk, warped buildings, duplicated landmarks, cartoon, illustration, 3D render
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| 도시야경 | riverfront skyline or rooftop skyline at dusk |
| 노을 도시 | dense downtown skyline with pink, orange, lavender sunset sky |
| 브릿지 야경 | suspension bridge over river with city lights behind it |
| 감성 R&B 도시 배경 | moody skyline with muted purple sky and warm lights |
| City Pop 배경 | glowing city skyline with soft sunset sky and clean composition |
| Chill playlist 배경 | calm skyline with open sky space and gentle reflections |
| 새벽 도시 | blue hour skyline with soft haze and fewer lights |
| 뉴욕 감성 | metropolitan skyline, bridge, river reflections, without copying exact landmarks unless requested |

---

#### 여름 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\여름`

선택한 레퍼런스 폴더가 **여름** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. 그 외 배경에는 적용하지 않는다.

**레퍼런스는 장면 복제가 아닌 여름 분위기·햇빛·색감·계절감·개방감 참조용으로만 사용한다.**

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 요소를 새롭게 조합한다:
- 도로 / 해변선 / 수면 / 파라솔 / 인물 배치 / 시점 / 시설물 배치

예시 장면:
- bright beach
- seaside walkway
- coastal road
- resort poolside
- outdoor summer cafe
- tropical promenade
- harbor village
- beach umbrellas and shoreline
- vacation boardwalk
- summer open-air leisure scene

##### 스타일 방향

- natural real-life summer photo
- bright summer sunlight
- clear blue sky if appropriate
- vivid turquoise or warm seasonal tones
- fresh open atmosphere
- relaxed vacation mood
- realistic shadows
- natural colors
- casual real-world photography
- slightly imperfect framing
- everyday seasonal atmosphere
- mild lens softness
- not overly polished
- not cinematic
- not hyper-detailed

실제로 촬영한 여름 여행 사진 같은 자연스러운 결과를 목표로 한다.

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- CGI / obvious AI look / overly perfect composition
- hyperreal look / HDR-heavy rendering / oversaturated colors
- fantasy lighting / glossy surfaces / cartoon / illustration
- text / logo
- winter tones / autumn colors / dark or gloomy atmosphere

아래 표현은 가급적 사용하지 않는다:
- cinematic / ultra detailed / hyper detailed / dramatic lighting
- perfect composition / highly stylized

##### 여름 배경 공통 프롬프트 템플릿

```
A natural real-life summer photo of [scene], inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Bright summer sunlight, clear blue sky if appropriate, vivid turquoise or warm seasonal tones, fresh open atmosphere, relaxed vacation mood, realistic shadows, natural colors, casual real-world photography, slightly imperfect framing, everyday seasonal atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

`[scene]` 작성 규칙:
1. 여름 분위기를 벗어나지 않는다
2. 레퍼런스 이미지의 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구도, 다른 위치, 다른 장면이 되도록 설정한다
4. 주제가 구체적일수록 `[scene]`을 구체화하고, 추상적이면 여름 배경 안에서 자연스러운 장면을 선택한다

프롬프트 작성 시 아래 개념을 반드시 포함한다:
- mood / lighting / color palette / different composition / different viewpoint / different location

##### 여름 배경 프롬프트 예시

```
A natural real-life summer photo of a bright beach with clear water, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Bright summer sunlight, clear blue sky if appropriate, vivid turquoise or warm seasonal tones, fresh open atmosphere, relaxed vacation mood, realistic shadows, natural colors, casual real-world photography, slightly imperfect framing, everyday seasonal atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

```
A natural real-life summer photo of a quiet seaside walkway, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Bright summer sunlight, clear blue sky if appropriate, vivid turquoise or warm seasonal tones, fresh open atmosphere, relaxed vacation mood, realistic shadows, natural colors, casual real-world photography, slightly imperfect framing, everyday seasonal atmosphere, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy surfaces, cartoon, illustration, text, logo
```

---

#### 카페 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\카페`

선택한 레퍼런스 폴더가 **카페** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. 그 외 배경에는 적용하지 않는다.

**레퍼런스는 장면 복제가 아닌 카페 분위기·조명·색감·아날로그 텍스처 참조용으로만 사용한다.**

##### [scene] 작성 핵심 규칙

`[scene]`는 반드시 아래 조건을 만족해야 한다.

- **English only**
- 완성된 시각적 장면 문장 (단일 키워드 금지)
- 현실적인 카페 상황
- 명확한 주피사체
- 자연스러운 보조 소품
- 불가능한 오브젝트 조합 금지
- 레퍼런스 이미지 장면 직접 복사 금지

**나쁜 예:** `[커피]` / `coffee` / `cafe mood` / `emotional cafe`

**좋은 예:**
```
a warm ceramic cup of coffee on a small wooden cafe table with soft window light
a quiet cafe window seat with a latte, an open book, and gentle afternoon shadows
a cozy cafe table with a cup of black coffee, a small dessert plate, and muted warm light
a peaceful coffee shop corner with a cappuccino, a notebook, and natural indoor shadows
```

##### 커피 주제 전용 변환 규칙

입력 주제가 **커피**일 경우 아래 중 하나로 장면을 확장한다.

```
a ceramic cup of hot coffee on a wooden cafe table with soft window light
a warm latte in a ceramic cup beside an open book on a cozy cafe table
a cup of black coffee on a small cafe table with a spoon, napkin, and soft afternoon light
a cappuccino on a wooden table near a cafe window with gentle natural shadows
a quiet cafe table with coffee, a small dessert plate, and muted warm colors
```

커피는 반드시 음료로 표현한다: `coffee as a drink` / `hot coffee in a cup` / `latte in a ceramic cup` / `cappuccino with foam` / `black coffee in a simple mug`

커피를 아래처럼 해석하지 않는다: flowerpot / plant container / decorative object only / surreal object / cup filled with plants / cup used as a vase

##### 카페 소품 배치 규칙

아래 소품을 선택적으로 사용하되, 배치는 반드시 현실적이어야 한다.

`coffee cup` / `ceramic mug` / `saucer` / `small spoon` / `napkin` / `open book` / `notebook` / `wooden table` / `small dessert plate` / `window light` / `soft curtain` / `record player` / `speaker` / `flowers in a separate vase` / `small plant in a separate pot`

**좋은 예:** `a latte beside an open book and a small flower vase` / `a cappuccino near a window, with a speaker softly blurred in the background`

**나쁜 예:** `a plant growing inside a coffee cup` / `a flower replacing the coffee` / `a cactus inside a teacup instead of coffee`

##### 카페 배경 공통 프롬프트 템플릿

```
A natural real-life photo of [expanded cafe scene], inspired only by the mood, lighting, color palette, and soft analog texture of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy cafe atmosphere, warm indoor light, soft natural shadows, muted warm colors, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, surreal objects, plants inside coffee cups, flowers inside coffee cups, cup used as a flowerpot, cartoon, illustration, text, logo, brand name, watermark
```

##### 카페 배경 프롬프트 예시

**입력: 커피**
```
A natural real-life photo of a warm ceramic cup of hot coffee on a small wooden cafe table beside a spoon and folded napkin, inspired only by the mood, lighting, color palette, and soft analog texture of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy cafe atmosphere, warm indoor light, soft natural shadows, muted warm colors, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, surreal objects, plants inside coffee cups, flowers inside coffee cups, cup used as a flowerpot, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 라떼**
```
A natural real-life photo of a warm latte in a ceramic cup on a cozy cafe table beside an open book and soft afternoon window light, inspired only by the mood, lighting, color palette, and soft analog texture of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy cafe atmosphere, warm indoor light, soft natural shadows, muted warm colors, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, surreal objects, plants inside coffee cups, flowers inside coffee cups, cup used as a flowerpot, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 카페 음악**
```
A natural real-life photo of a cozy cafe music corner with a small speaker, a cup of coffee on a wooden table, and soft window light in the background, inspired only by the mood, lighting, color palette, and soft analog texture of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy cafe atmosphere, warm indoor light, soft natural shadows, muted warm colors, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, surreal objects, plants inside coffee cups, flowers inside coffee cups, cup used as a flowerpot, cartoon, illustration, text, logo, brand name, watermark
```

---

#### 하늘 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\하늘`

선택한 레퍼런스 폴더가 **하늘** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. (하늘, 구름, 맑은 하늘, 여름 하늘, 청량한 배경, 플레이리스트 배경용 하늘 주제 포함)

**레퍼런스는 장면 복제가 아닌 하늘 색감·구름 형태·밝기·공기감·계절감 참조용으로만 사용한다.**

플레이리스트 배경용일 경우 과도한 디테일을 줄이고 중앙 또는 상단에 여백을 충분히 남긴다.

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 원칙을 따른다:

- 하늘이 주 피사체가 되도록 구성한다
- 건물, 사람, 도로, 해변, 산 등은 요청이 있을 때만 최소한으로 포함한다
- 배경용 이미지일 경우 복잡한 사물이나 강한 랜드마크를 넣지 않는다
- 구름은 자연스럽고 불규칙해야 하며 너무 완벽하거나 반복적인 패턴을 피한다
- 하늘 색상은 자연스러운 파란색을 유지하고 과도하게 형광빛이 나지 않도록 한다

예시 장면:
- clear blue sky with soft white clouds
- bright summer sky with fluffy clouds
- open sky background with gentle cloud shapes
- wide blue sky with scattered cumulus clouds
- peaceful sky above a distant horizon
- minimal sky background with soft cloud edges
- fresh morning sky with light clouds
- warm afternoon sky with natural sunlight
- clean playlist background with blue sky and white clouds
- airy sky background with large negative space

##### 스타일 방향

- natural real-life photo
- clear blue sky
- soft white clouds
- bright natural daylight
- fresh airy atmosphere
- natural cloud shapes
- realistic sky gradient
- clean open background
- slightly imperfect natural framing
- casual real-world photography
- mild lens softness
- not overly polished
- not cinematic
- not hyper-detailed

실제로 맑은 날 촬영한 자연스러운 하늘 사진을 목표로 한다.

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- CGI / obvious AI look / overly perfect cloud shapes / repeated cloud patterns
- fantasy sky / dramatic storm clouds / surreal colors / HDR-heavy rendering
- oversaturated blue / glowing artificial clouds / cartoon / illustration
- text / logo / watermark / aircraft (요청 없을 시) / birds (요청 없을 시) / buildings (요청 없을 시)

아래 표현은 가급적 사용하지 않는다:
- cinematic / ultra detailed / hyper detailed / dramatic lighting
- fantasy atmosphere / epic sky / perfect composition / highly stylized / vibrant colors

##### 하늘 배경 공통 프롬프트 템플릿

```
A natural real-life photo of [expanded sky scene], inspired only by the mood, lighting, color palette, and cloud softness of the reference image, but with a different cloud arrangement and different framing. Clear blue sky, soft white clouds, bright natural daylight, fresh airy atmosphere, realistic sky gradient, natural cloud shapes, clean open background, slightly imperfect natural framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect clouds, repeated cloud patterns, fantasy sky, surreal colors, HDR, oversaturated blue, cartoon, illustration, text, logo, watermark, aircraft, birds, buildings
```

##### [expanded sky scene] 작성 규칙

`[expanded sky scene]`는 입력된 주제에 맞게 완성된 영어 장면 문장으로 확장한다.

1. 하늘 배경 범위를 벗어나지 않는다
2. 레퍼런스 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구름 배치, 다른 프레이밍이 되도록 설정한다
4. "하늘", "sky" 등 단어만 그대로 넣지 않고 반드시 완성된 장면 문장으로 확장한다
5. 플레이리스트 배경용일 경우 복잡한 피사체 없이 여백이 많은 장면으로 구성한다

예시:
```
a clear blue sky with soft scattered white clouds and large open negative space
a bright summer sky with fluffy cumulus clouds and open negative space
a peaceful blue sky background with gentle cloud shapes
a clean open sky with natural white clouds and soft daylight
a fresh morning sky with light clouds and a calm airy mood
a wide blue sky background with soft clouds around the edges
a simple playlist background of blue sky and white clouds
```

**단어형 입력 처리** — 짧은 단어 입력 시 그대로 쓰지 않고 완성된 장면 문장으로 변환한다.

나쁜 예: `A natural real-life photo of sky...` / `A natural real-life photo of [하늘]...`

좋은 예: `A natural real-life photo of a clear blue sky with soft scattered white clouds and large open negative space...`

##### 하늘 배경 프롬프트 예시

**입력: 하늘**
```
A natural real-life photo of a clear blue sky with soft scattered white clouds and large open negative space, inspired only by the mood, lighting, color palette, and cloud softness of the reference image, but with a different cloud arrangement and different framing. Clear blue sky, soft white clouds, bright natural daylight, fresh airy atmosphere, realistic sky gradient, natural cloud shapes, clean open background, slightly imperfect natural framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect clouds, repeated cloud patterns, fantasy sky, surreal colors, HDR, oversaturated blue, cartoon, illustration, text, logo, watermark, aircraft, birds, buildings
```

**입력: 구름**
```
A natural real-life photo of a wide blue sky with soft fluffy white clouds arranged naturally around the frame, inspired only by the mood, lighting, color palette, and cloud softness of the reference image, but with a different cloud arrangement and different framing. Clear blue sky, bright natural daylight, fresh airy atmosphere, realistic sky gradient, natural cloud shapes, clean open background, slightly imperfect natural framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect clouds, repeated cloud patterns, fantasy sky, surreal colors, HDR, oversaturated blue, cartoon, illustration, text, logo, watermark, aircraft, birds, buildings
```

**입력: 여름 하늘**
```
A natural real-life photo of a bright summer sky with vivid but natural blue color, soft cumulus clouds, and a clean open background, inspired only by the mood, lighting, color palette, and cloud softness of the reference image, but with a different cloud arrangement and different framing. Bright natural daylight, fresh airy atmosphere, realistic sky gradient, natural cloud shapes, slightly imperfect natural framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect clouds, repeated cloud patterns, fantasy sky, surreal colors, HDR, oversaturated blue, cartoon, illustration, text, logo, watermark, aircraft, birds, buildings
```

**입력: 플레이리스트 배경**
```
A natural real-life photo of a clean open blue sky background with soft white clouds around the edges and large empty space for a playlist visual, inspired only by the mood, lighting, color palette, and cloud softness of the reference image, but with a different cloud arrangement and different framing. Clear blue sky, bright natural daylight, fresh airy atmosphere, realistic sky gradient, natural cloud shapes, minimal background composition, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect clouds, repeated cloud patterns, fantasy sky, surreal colors, HDR, oversaturated blue, cartoon, illustration, text, logo, watermark, aircraft, birds, buildings
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| 맑음, 청량함, 기본 하늘 | clear blue sky with soft scattered clouds |
| 여름, 휴양, 밝은 감성 | bright summer sky with fluffy cumulus clouds |
| 플레이리스트 배경 | clean open sky with large negative space |
| 감성, 차분함, 휴식 | peaceful sky background with gentle cloud shapes |
| 아침, 희망, 산뜻함 | fresh morning sky with light clouds |
| 넓은 배경, 썸네일용 | wide blue sky with clouds around the edges |

---

#### 공부 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\공부`

선택한 레퍼런스 폴더가 **공부** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. (공부, 스터디, 책상, 집중, 노트북 작업, 학습 공간, 감성 공부방, 플레이리스트용 공부 배경 주제 포함)

**레퍼런스는 장면 복제가 아닌 공부 분위기·조명·색감·책상 질감·집중감·공기감 참조용으로만 사용한다.**

책상은 완벽하게 정돈된 쇼룸이 아닌, 실제로 공부 중인 자연스러운 생활감이 있어야 한다.

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 원칙을 따른다:

- 레퍼런스 이미지의 특정 책상 배치나 물건 위치를 그대로 따라하지 않는다
- 노트북, 책, 태블릿, 계산기, 필기구, 책상 조명, 물병, 작은 식물 등은 주제에 맞을 때만 선택적으로 사용한다
- 전체 인상은 조용하고 집중하기 좋은 공부 공간이어야 한다
- 과도하게 깔끔한 광고 이미지나 쇼룸 같은 느낌을 피한다
- 실제 공부 중인 자연스러운 어수선함은 허용하되 너무 지저분하게 만들지 않는다

예시 장면:
- cozy study desk beside a window
- quiet desk setup with laptop, open textbook, and notes
- warm evening study room with desk lamp
- morning study desk with natural window light
- focused student workspace with books and stationery
- calm home study corner with laptop and notebook
- rainy window study desk with warm lamp light
- exam preparation desk with open books and calculator
- minimal study desk with tablet, notebook, and soft shadows
- playlist background study room with cozy lighting
- late-night study setup with lamp, laptop, and papers
- peaceful reading desk with books and coffee

##### 스타일 방향

- natural real-life photo
- cozy study atmosphere
- warm desk lamp light
- soft window light
- natural indoor shadows
- muted warm colors
- realistic desk texture
- lived-in study space
- slightly imperfect framing
- casual real-world photography
- mild lens softness
- quiet focus mood
- calm playlist background mood
- not overly polished
- not cinematic
- not hyper-detailed

실제 방이나 공부 공간에서 자연스럽게 촬영한 감성적인 공부 사진을 목표로 한다.

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- CGI / obvious AI look / overly perfect composition / hyperreal look
- HDR-heavy rendering / oversaturated colors / fantasy lighting
- glossy luxury interior / showroom-like perfection
- fake laptop screen text / readable text on books or papers / distorted keyboard
- impossible desk arrangement / cartoon / illustration / text / logo / brand name / watermark

아래 표현은 가급적 사용하지 않는다:
- cinematic / ultra detailed / hyper detailed / dramatic lighting
- perfect composition / luxury interior / highly stylized / vibrant colors

##### 공부 배경 공통 프롬프트 템플릿

```
A natural real-life photo of [expanded study scene], inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy study atmosphere, warm desk lamp light, soft window light, natural indoor shadows, muted warm colors, realistic desk texture, lived-in study space, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, showroom-like perfection, fake readable text, distorted keyboard, impossible desk arrangement, cartoon, illustration, text, logo, brand name, watermark
```

##### [expanded study scene] 작성 규칙

`[expanded study scene]`는 입력된 주제에 맞게 완성된 영어 장면 문장으로 확장한다.

1. 공부 주제 범위를 벗어나지 않는다
2. 레퍼런스 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구도, 다른 시점, 다른 소품 배치가 되도록 설정한다
4. "공부"라는 단어만 그대로 넣지 않고 반드시 완성된 영어 장면 문장으로 확장한다
5. 책이나 노트의 글자는 읽을 수 없거나 흐릿해야 한다
6. 노트북 화면이 필요한 경우 실제 텍스트가 아닌 흐릿한 문서 화면 또는 은은한 화면빛으로 표현한다

예시:
```
a cozy study desk beside a window with an open textbook, laptop, and warm desk lamp
a quiet home study corner with a laptop, notebook, pens, and soft evening light
a focused exam preparation desk with open books, calculator, notes, and natural indoor shadows
a peaceful reading desk near a window with books, a notebook, and warm muted colors
a late-night study setup with a desk lamp, laptop, papers, and a calm focused mood
a morning study desk with soft window light, open notebook, and simple stationery
a cozy playlist background study room with books, laptop, and warm lamp light
a realistic student desk with tablet, notebook, pens, and a slightly lived-in arrangement
```

**단어형 입력 처리** — 짧은 단어 입력 시 그대로 쓰지 않고 완성된 장면 문장으로 변환한다.

나쁜 예: `A natural real-life photo of study...` / `A natural real-life photo of [공부]...`

좋은 예: `A natural real-life photo of a cozy study desk beside a window with an open textbook, laptop, notebook, pens, and warm desk lamp light...`

##### 공부 배경 프롬프트 예시

**입력: 공부**
```
A natural real-life photo of a cozy study desk beside a window with an open textbook, laptop, notebook, pens, and warm desk lamp light, inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy study atmosphere, warm desk lamp light, soft window light, natural indoor shadows, muted warm colors, realistic desk texture, lived-in study space, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, glossy luxury interior, showroom-like perfection, fake readable text, distorted keyboard, impossible desk arrangement, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 시험공부**
```
A natural real-life photo of a focused exam preparation desk with open textbooks, a calculator, handwritten notes, pens, and a warm desk lamp near a window, inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy study atmosphere, natural indoor shadows, muted warm colors, realistic desk texture, lived-in study space, casual real-world photography, slightly imperfect framing, mild lens softness, calm focus mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, fake readable text, distorted keyboard, impossible desk arrangement, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 밤공부**
```
A natural real-life photo of a quiet late-night study setup with a laptop, open books, scattered notes, and a warm desk lamp creating soft shadows on a wooden desk, inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy study atmosphere, warm indoor light, muted warm colors, realistic desk texture, lived-in study space, casual real-world photography, slightly imperfect framing, mild lens softness, calm playlist background mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, fake readable text, distorted keyboard, impossible desk arrangement, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 독서**
```
A natural real-life photo of a peaceful reading desk near a window with an open book, a notebook, a cup of tea, and soft natural light, inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Cozy study atmosphere, soft window light, natural indoor shadows, muted warm colors, realistic desk texture, casual real-world photography, slightly imperfect framing, mild lens softness, calm reading mood, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, fake readable text, cartoon, illustration, text, logo, brand name, watermark
```

**입력: 플레이리스트 배경**
```
A natural real-life photo of a cozy study room background with a wooden desk, laptop, books, notebook, soft desk lamp light, and enough open space for a playlist visual, inspired only by the mood, lighting, color palette, and quiet focus atmosphere of the reference image, but with a different composition, different viewpoint, and different object arrangement. Calm study playlist mood, warm indoor light, muted warm colors, realistic desk texture, lived-in study space, casual real-world photography, slightly imperfect framing, mild lens softness, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, fake readable text, distorted keyboard, cartoon, illustration, text, logo, brand name, watermark
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| 공부, 스터디, 집중 | cozy study desk beside a window with books and laptop |
| 시험공부, 수험생, 문제풀이 | exam preparation desk with textbooks, calculator, notes, and pens |
| 노트북 작업, 과제, 리포트 | laptop study desk with notebook and warm lamp light |
| 독서, 책, 조용함 | peaceful reading desk with open book and soft window light |
| 밤공부, 새벽공부 | late-night study setup with warm desk lamp and soft shadows |
| 플레이리스트 배경 | cozy study room background with open space and calm lighting |
| 감성공부, 집중음악 | warm study desk with soft lighting and calm playlist mood |

---

#### 하이틴 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\하이틴`

선택한 레퍼런스 폴더가 **하이틴** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. (감성 R&B, R&B playlist, 하이틴, 청춘 로맨스, 여름 로맨스, 영화 스틸컷, 감성 인물 장면 주제 포함)

**레퍼런스는 인물 얼굴·포즈 복제가 아닌 영화적 분위기·색감·조명·필름 질감·감정선·카메라 거리감 참조용으로만 사용한다.**

인물은 과도하게 포즈를 취한 모델이 아닌 우연히 포착된 장면처럼 자연스러워야 하며, 실제 배우나 특정 유명인을 닮지 않도록 한다.

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 원칙을 따른다:

- 인물 수는 주제에 맞게 1명 또는 2명으로 자연스럽게 선택한다
- 얼굴을 너무 정면 클로즈업으로 과하게 만들지 않는다
- 카메라가 우연히 포착한 듯한 자연스러운 시선을 유지한다
- 패션은 심플하고 현실적인 여름 캐주얼 스타일을 사용한다
- 흡연, 담배, 과도한 노출, 선정적인 분위기는 넣지 않는다
- 감성 R&B에 어울리는 쓸쓸함, 설렘, 회상, 거리감, 여름밤의 여운을 표현한다

예시 장면:
- two young adults sitting on a seaside boardwalk at golden hour
- a quiet summer beach moment between two young adults
- a nostalgic couple scene near the ocean with warm sunlight
- two friends sitting in a parked car at sunset
- a young couple walking near a pier in soft afternoon light
- a lonely R&B playlist scene with one person looking out at the sea
- a candid coming-of-age film still on a summer afternoon
- a warm nostalgic boardwalk scene with ocean in the background
- a quiet roadside diner moment with soft window light
- a late summer evening scene with emotional distance between two people

##### 스타일 방향

- nostalgic coming-of-age film still
- emotional R&B playlist mood
- natural real-life photography
- warm summer sunlight
- soft film grain
- slightly faded colors
- natural skin tones
- candid expression
- shallow depth of field
- imperfect framing
- relaxed coastal atmosphere
- quiet romantic tension
- soft background blur
- 90s or early 2000s film photo feeling
- not overly polished
- not cinematic blockbuster
- not glossy fashion editorial

광고 사진이 아닌 오래된 청춘 영화의 한 장면처럼 자연스럽고 아련한 사진을 목표로 한다.

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- CGI / obvious AI look / plastic skin / overly perfect faces / fashion magazine pose
- glossy editorial lighting / luxury styling / dramatic blockbuster lighting
- hyperreal rendering / HDR-heavy colors / oversaturated colors / fantasy atmosphere
- exact celebrity likeness / recognizable actor / copied movie scene
- smoking / cigarette / sensual pose / explicit content
- text / logo / watermark

아래 표현은 가급적 사용하지 않는다:
- ultra detailed / hyper detailed / perfect face / perfect composition
- glamour photography / luxury fashion / dramatic cinematic lighting / vibrant colors

##### 하이틴 배경 공통 프롬프트 템플릿

```
A natural real-life photo of [expanded emotional R&B scene], inspired only by the mood, lighting, color palette, film grain, and emotional atmosphere of the reference image, but with different people, different composition, different viewpoint, and different setting. Nostalgic coming-of-age film still, emotional R&B playlist mood, warm summer sunlight, slightly faded colors, natural skin tones, candid expression, shallow depth of field, soft background blur, imperfect framing, relaxed coastal atmosphere, quiet romantic tension, not overly polished, not glossy. --ar 16:9 --style raw --s 20 --v 6 --no CGI, AI look, plastic skin, overly perfect faces, celebrity likeness, copied movie scene, smoking, cigarette, sensual pose, explicit content, HDR, oversaturated colors, cartoon, illustration, text, logo, watermark
```

##### [expanded emotional R&B scene] 작성 규칙

`[expanded emotional R&B scene]`는 입력된 주제에 맞게 완성된 영어 장면 문장으로 확장한다.

1. 입력 단어를 그대로 넣지 않는다
2. "감성 R&B"만 입력된 경우 반드시 인물과 감정이 있는 장면으로 확장한다
3. 레퍼런스의 인물, 얼굴, 포즈를 그대로 복제하지 않는다
4. 배경은 해변, 보드워크, 자동차, 도심 야외, 다이너, 여름 거리 등 감성 R&B에 어울리는 장소로 새롭게 구성한다
5. 인물은 실제 존재하는 배우나 유명인을 닮지 않도록 한다
6. 청춘 영화 감성은 유지하되 과한 드라마 포스터처럼 만들지 않는다
7. 흡연 장면은 생성하지 않는다

예시:
```
two young adults sitting on a seaside boardwalk during a warm summer afternoon
a young woman looking away from a young man near the ocean, with quiet emotional tension
a lonely young adult sitting by the beach at golden hour, lost in thought
two young adults in a parked car near the coast, sharing a quiet emotional moment
a nostalgic summer boardwalk scene with ocean wind and soft sunlight
a young couple walking apart near a pier, with emotional distance between them
a candid R&B playlist scene of one person leaning against a beach railing at sunset
a quiet late-summer romance scene near the ocean with soft film grain
```

**단어형 입력 처리** — 짧은 단어 입력 시 그대로 쓰지 않고 완성된 장면 문장으로 변환한다.

나쁜 예: `A natural real-life photo of emotional R&B...` / `A high teen image...`

좋은 예: `A natural real-life photo of two young adults sitting on a seaside boardwalk during a warm summer afternoon, sharing a quiet emotional moment...`

##### 하이틴 배경 프롬프트 예시

**입력: 감성 R&B**
```
A natural real-life photo of two young adults sitting on a seaside boardwalk during a warm summer afternoon, sharing a quiet emotional moment, inspired only by the mood, lighting, color palette, film grain, and emotional atmosphere of the reference image, but with different people, different composition, different viewpoint, and different setting. Nostalgic coming-of-age film still, emotional R&B playlist mood, warm summer sunlight, slightly faded colors, natural skin tones, candid expression, shallow depth of field, soft background blur, imperfect framing, relaxed coastal atmosphere, quiet romantic tension, not overly polished, not glossy. --ar 16:9 --style raw --s 20 --v 6 --no CGI, AI look, plastic skin, overly perfect faces, celebrity likeness, copied movie scene, smoking, cigarette, sensual pose, explicit content, HDR, oversaturated colors, cartoon, illustration, text, logo, watermark
```

**입력: 첫사랑**
```
A natural real-life photo of two young adults walking near a quiet beach pier in warm afternoon light, with shy expressions and subtle emotional distance, inspired only by the mood, lighting, color palette, film grain, and emotional atmosphere of the reference image, but with different people, different composition, different viewpoint, and different setting. Nostalgic coming-of-age film still, emotional R&B playlist mood, soft summer wind, slightly faded colors, natural skin tones, candid expression, shallow depth of field, imperfect framing, quiet romantic tension, not overly polished, not glossy. --ar 16:9 --style raw --s 20 --v 6 --no CGI, AI look, plastic skin, overly perfect faces, celebrity likeness, copied movie scene, smoking, cigarette, sensual pose, explicit content, HDR, oversaturated colors, cartoon, illustration, text, logo, watermark
```

**입력: 이별**
```
A natural real-life photo of one young adult sitting alone near a seaside railing at golden hour, looking away with a quiet heartbroken expression, inspired only by the mood, lighting, color palette, film grain, and emotional atmosphere of the reference image, but with a different composition, different viewpoint, and different setting. Nostalgic coming-of-age film still, emotional R&B playlist mood, warm fading sunlight, slightly faded colors, natural skin tones, candid expression, shallow depth of field, soft ocean background blur, imperfect framing, lonely summer atmosphere, not overly polished, not glossy. --ar 16:9 --style raw --s 20 --v 6 --no CGI, AI look, plastic skin, overly perfect faces, celebrity likeness, copied movie scene, smoking, cigarette, sensual pose, explicit content, HDR, oversaturated colors, cartoon, illustration, text, logo, watermark
```

**입력: 플레이리스트 배경**
```
A natural real-life photo of a nostalgic summer boardwalk scene with two young adults in the distance and the ocean softly blurred behind them, leaving open space for a playlist visual, inspired only by the mood, lighting, color palette, film grain, and emotional atmosphere of the reference image, but with different people, different composition, different viewpoint, and different setting. Emotional R&B playlist mood, warm summer sunlight, slightly faded colors, natural skin tones, candid real-life feeling, shallow depth of field, imperfect framing, relaxed coastal atmosphere, not overly polished, not glossy. --ar 16:9 --style raw --s 20 --v 6 --no CGI, AI look, plastic skin, overly perfect faces, celebrity likeness, copied movie scene, smoking, cigarette, sensual pose, explicit content, HDR, oversaturated colors, cartoon, illustration, text, logo, watermark
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| 감성 R&B, 청춘, 설렘 | two young adults sharing a quiet emotional moment near the ocean |
| 첫사랑, 하이틴 로맨스 | shy young adults near a beach pier or summer boardwalk |
| 이별, 그리움, 외로움 | one person alone near the ocean or seaside railing |
| 여름 로맨스 | warm summer afternoon boardwalk or beachside scene |
| 밤 감성 R&B | parked car, quiet street, or coastal night scene with soft available light |
| 플레이리스트 배경 | people smaller in frame, open space, soft background blur |

---

#### Groove Hiphop 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\Groove hiphop`

선택한 레퍼런스 폴더가 **Groove Hiphop** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. (Groove Hip-hop, Chill Pop, Boom Bap, Lo-fi Groove, 플레이리스트 커버용 일러스트 주제 포함)

**이 지침은 실사 사진이 아닌 손그림 감성의 2D 일러스트 스타일에만 적용한다.**

**레퍼런스는 그림 톤·선 굵기·색감·질감·구성감·유쾌한 무드 참조용으로만 사용한다. 레퍼런스 속 특정 캐릭터, 자동차, 구도, 배경을 그대로 재현하지 않는다.**

##### 핵심 스타일 방향

- whimsical hand-drawn 2D illustration
- playful cartoon style
- thick black outlines
- flat bold colors
- simple rounded shapes
- doodle-like texture
- slightly imperfect linework
- colorful surreal landscape
- funky groove mood
- upbeat hip-hop playlist vibe
- retro cartoon feeling
- minimal shading
- no realistic rendering
- no 3D look

##### 색감 방향

레퍼런스 이미지의 색감을 참조하되 주제에 맞게 변형할 수 있다.

기본 색감:
- mustard yellow sky / warm yellow background
- coral red or tomato red objects
- teal blue road, river, or ground
- orange and red trees / pastel pink land
- light gray cartoon clouds / black hand-drawn outlines

변형 예시:
- yellow sky + teal road + red car
- pink ground + orange trees + blue river
- mint background + red speaker + yellow objects
- warm pastel city + teal shadows + black outlines

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 원칙을 따른다:

- 동물 캐릭터, 자동차, 음악 소품, 길, 숲, 도시, 구름 등을 자유롭게 조합한다
- 스피커, LP, 헤드폰, 음악 노트, 카세트, 라디오 같은 소품을 선택적으로 사용한다
- 소품을 과하게 많이 넣지 않는다
- 16:9 화면에서 잘 보이도록 구도를 구성한다

예시 장면:
- a funky animal character driving through a colorful surreal city
- a cartoon cat cruising in a red car with music notes floating around
- a playful dog DJ driving through a groovy autumn landscape
- a retro car dashboard with a colorful road and dancing trees
- a whimsical hip-hop road trip through a surreal forest
- a cartoon animal listening to music in a bright red car
- a funky playlist cover scene with speakers, records, and a colorful street
- a surreal hand-drawn city road with music-inspired objects
- a cute animal character on a groove hip-hop road trip

##### 금지 방향

프롬프트에 아래 결과가 나오지 않도록 유도한다:

- photorealistic / realistic photo / 3D render / CGI
- anime style / oil painting / watercolor realism / glossy digital art
- overly detailed background / cinematic lighting / hyperreal texture
- perfect clean vector look / luxury car realism / real animal anatomy
- scary or dark mood / text / logo / watermark

##### Groove Hiphop 공통 프롬프트 템플릿

```
A whimsical hand-drawn 2D illustration of [expanded groove hip-hop scene], inspired only by the playful illustration tone, thick black outlines, flat bold colors, doodle-like texture, and funky color palette of the reference image, but with a different character, different composition, and different setting. Groove hip-hop playlist cover mood, playful cartoon style, slightly imperfect linework, simple rounded shapes, mustard yellow sky, teal blue accents, coral red objects, orange trees, light gray cartoon clouds, minimal shading, retro funky feeling, not realistic, not 3D. --ar 16:9 --s 75 --v 6 --no photorealistic, realistic photo, 3D render, CGI, anime, glossy digital art, cinematic lighting, hyperreal, text, logo, watermark
```

> **API 호출 시 파라미터 변경 (실사 사진 섹션과 다름)**
> - `stylize`: **75** (기본값 100 대신)
> - `noPrompt`: `"photorealistic, 3D render, CGI, anime, cinematic lighting, text, logo, watermark"` (인물·얼굴 제한 제거)
> - 프롬프트에서 `--style raw` 제거

##### [expanded groove hip-hop scene] 작성 규칙

`[expanded groove hip-hop scene]`는 입력된 주제에 맞게 구체적인 영어 장면 문장으로 확장한다.

나쁜 예: `Groove hip-hop` / `A groove hip-hop image` / `[Groove hiphop]`

좋은 예:
```
a funky cartoon dog driving a red car through a surreal colorful road with music notes floating in the air
a playful cartoon cat wearing headphones while cruising through a bright hand-drawn city street
a retro car dashboard view with a cute animal character, colorful trees, cartoon clouds, and a funky road trip mood
a whimsical animal DJ driving through a surreal autumn landscape with speakers and vinyl records in the background
```

##### Groove Hiphop 프롬프트 예시

**입력: Groove Hip-hop**
```
A whimsical hand-drawn 2D illustration of a funky cartoon dog driving a red car through a surreal colorful road with music notes floating in the air, inspired only by the playful illustration tone, thick black outlines, flat bold colors, doodle-like texture, and funky color palette of the reference image, but with a different character, different composition, and different setting. Groove hip-hop playlist cover mood, playful cartoon style, slightly imperfect linework, simple rounded shapes, mustard yellow sky, teal blue road, coral red objects, orange trees, light gray cartoon clouds, minimal shading, retro funky feeling, not realistic, not 3D. --ar 16:9 --s 75 --v 6 --no photorealistic, realistic photo, 3D render, CGI, anime, glossy digital art, cinematic lighting, hyperreal, text, logo, watermark
```

**입력: Chill Hip-hop**
```
A whimsical hand-drawn 2D illustration of a relaxed cartoon cat wearing headphones in a colorful car, driving through a soft surreal landscape with round trees and small cartoon clouds, inspired only by the playful illustration tone, thick black outlines, flat bold colors, doodle-like texture, and funky color palette of the reference image, but with a different character, different composition, and different setting. Chill hip-hop playlist cover mood, playful cartoon style, slightly imperfect linework, simple rounded shapes, warm yellow sky, teal blue accents, coral red dashboard, orange trees, minimal shading, retro cozy feeling, not realistic, not 3D. --ar 16:9 --s 75 --v 6 --no photorealistic, realistic photo, 3D render, CGI, anime, glossy digital art, cinematic lighting, hyperreal, text, logo, watermark
```

**입력: Boom Bap Drive**
```
A whimsical hand-drawn 2D illustration of a retro car interior with a cute animal character listening to boom bap music, colorful speakers, a teal road ahead, orange trees, and small gray cartoon clouds, inspired only by the playful illustration tone, thick black outlines, flat bold colors, doodle-like texture, and funky color palette of the reference image, but with a different character, different composition, and different setting. Boom bap playlist cover mood, playful cartoon style, slightly imperfect linework, simple rounded shapes, mustard yellow background, coral red car interior, teal blue road, minimal shading, retro funky feeling, not realistic, not 3D. --ar 16:9 --s 75 --v 6 --no photorealistic, realistic photo, 3D render, CGI, anime, glossy digital art, cinematic lighting, hyperreal, text, logo, watermark
```

**입력: 플레이리스트 배경**
```
A whimsical hand-drawn 2D illustration of a colorful groove hip-hop road trip scene with a small cartoon animal character, a red car, teal road, orange trees, soft gray clouds, and open space for a playlist visual, inspired only by the playful illustration tone, thick black outlines, flat bold colors, doodle-like texture, and funky color palette of the reference image, but with a different character, different composition, and different setting. Playful hip-hop playlist cover mood, slightly imperfect linework, simple rounded shapes, mustard yellow sky, coral red objects, teal blue accents, minimal shading, retro funky feeling, not realistic, not 3D. --ar 16:9 --s 75 --v 6 --no photorealistic, realistic photo, 3D render, CGI, anime, glossy digital art, cinematic lighting, hyperreal, text, logo, watermark
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| Groove Hip-hop | funky cartoon animal driving through a colorful surreal road |
| Chill Hip-hop | relaxed animal character with headphones in a cozy colorful car |
| Boom Bap | retro car interior, speakers, cassette, vinyl, strong groove elements |
| Drive Playlist | dashboard view, road ahead, playful trees, music notes |
| Autumn Groove | orange trees, yellow sky, teal road, warm playful landscape |
| City Groove | hand-drawn funky city street with cars, music elements |
| Playlist Background | open composition, simple scene, enough empty space |

#### 드라이브 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\드라이브`

선택한 레퍼런스 폴더가 **드라이브** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. 그 외 배경에는 적용하지 않는다.

**레퍼런스는 장면 복제가 아닌 드라이브 분위기·도로·자연·공기감 참조용으로만 사용한다.**

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 요소를 새롭게 조합한다:
- 도로 형태 / 주변 자연 / 시점(1인칭 대시보드·측면·항공) / 시간대 / 식물 배치

예시 장면:
- winding forest road
- open highway through countryside
- tree-lined mountain road at golden hour
- coastal cliff road with ocean view
- misty morning forest drive
- straight road through vast plains
- autumn country road with fallen leaves
- sunlit road through pine forest
- empty road under wide open sky
- curving road with green hills

##### 스타일 방향

- natural real-life driving photo
- open road atmosphere
- natural light (golden hour or soft daylight preferred)
- sense of movement and freedom
- green or seasonal natural tones
- realistic shadows and depth
- slightly imperfect framing
- not overly polished
- not cinematic
- no people visible

##### 금지 방향

- CGI / obvious AI look / overly perfect composition
- hyperreal look / HDR-heavy rendering / oversaturated colors
- fantasy lighting / glossy surfaces / cartoon / illustration
- text / logo / signage
- crowded highway / urban traffic jam

##### 드라이브 배경 공통 프롬프트 템플릿

```
A natural real-life driving photo of [scene], inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Open road atmosphere, natural light, sense of movement and freedom, green or seasonal natural tones, realistic shadows and depth, slightly imperfect framing, not overly polished, not cinematic, no people visible. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, cartoon, illustration, text, logo, crowded traffic
```

`[scene]` 작성 규칙:
1. 도로와 자연 요소를 조합한다
2. 레퍼런스 이미지의 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구도, 다른 위치, 다른 장면이 되도록 설정한다

##### 드라이브 배경 프롬프트 예시

```
A natural real-life driving photo of a winding road through a sunlit pine forest, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Open road atmosphere, natural light, sense of movement and freedom, green natural tones, realistic shadows and depth, slightly imperfect framing, not overly polished, not cinematic, no people visible. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, fantasy lighting, cartoon, illustration, text, logo
```

```
A natural real-life driving photo of an open highway stretching through golden plains at sunset, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Open road atmosphere, warm golden hour light, sense of freedom and movement, seasonal natural tones, slightly imperfect framing, not overly polished, not cinematic, no people visible. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, cartoon, illustration, text, logo
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| Chillwave / 신스팝 드라이브 | misty coastal road or twilight highway with soft atmospheric haze |
| Late Night R&B 드라이브 | empty night road with distant city glow or moonlit country lane |
| 가을 드라이브 | tree-lined autumn road with orange and yellow leaves |
| 여름 드라이브 | coastal cliff road with bright sea view |
| 새벽 드라이브 | misty morning forest road with soft diffused light |

---

#### 어쿠스틱팝 배경 전용 프롬프트 기준

레퍼런스 폴더 경로: `{referenceDir}\어쿠스틱팝`

선택한 레퍼런스 폴더가 **어쿠스틱팝** 폴더일 경우에만 이 섹션의 프롬프트 규칙을 적용한다. 그 외 배경에는 적용하지 않는다.

**레퍼런스는 장면 복제가 아닌 자연광·온기·개방감·평온함 참조용으로만 사용한다.**

##### 장면 구성 원칙

장면은 레퍼런스와 **다르게** 구성하며, 아래 요소를 새롭게 조합한다:
- 자연 환경 / 인물 유무 / 시점 / 시간대 / 소품(자전거·피크닉·악기 등)

예시 장면:
- sunlit green meadow with wildflowers
- peaceful picnic on a grassy hill
- golden hour field with scattered trees
- open countryside path under warm sky
- gentle hillside overlooking a valley
- quiet lakeside with soft reflections
- afternoon sunlight through tree branches
- warm sunset over open farmland
- breezy coastal cliff with green grass
- calm garden with morning light

##### 스타일 방향

- warm natural daylight or golden hour
- soft and gentle atmosphere
- open outdoor space
- natural greens, warm yellows, soft sky blues
- peaceful and unhurried mood
- realistic natural photo feel
- slightly soft focus or gentle lens flare acceptable
- not overly polished
- not cinematic
- airy and breathing composition

##### 금지 방향

- CGI / obvious AI look / overly perfect composition
- hyperreal look / HDR-heavy rendering / oversaturated colors
- dark or moody atmosphere
- fantasy lighting / glossy surfaces / cartoon / illustration
- text / logo
- urban or industrial backgrounds

##### 어쿠스틱팝 배경 공통 프롬프트 템플릿

```
A warm natural real-life photo of [scene], inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Warm natural daylight or golden hour, soft and gentle atmosphere, open outdoor space, natural greens and warm seasonal tones, peaceful and unhurried mood, slightly soft focus, not overly polished, not cinematic, airy composition. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, dark atmosphere, cartoon, illustration, text, logo, urban background
```

`[scene]` 작성 규칙:
1. 자연·야외 공간을 중심으로 구성한다
2. 레퍼런스 이미지의 장면을 그대로 설명하지 않는다
3. 레퍼런스와 다른 구도, 다른 위치, 다른 장면이 되도록 설정한다

##### 어쿠스틱팝 배경 프롬프트 예시

```
A warm natural real-life photo of a sunlit green meadow with scattered wildflowers and a gentle breeze, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Warm golden hour light, soft and gentle atmosphere, open outdoor space, natural greens and soft yellows, peaceful and unhurried mood, slightly soft focus, not overly polished, not cinematic, airy composition. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, dark atmosphere, cartoon, illustration, text, logo
```

```
A warm natural real-life photo of a quiet hillside overlooking a valley at golden hour, inspired only by the mood, lighting, and color palette of the reference image, but with a different composition, different viewpoint, and different location. Warm afternoon light, gentle and peaceful atmosphere, natural greens and warm earth tones, open sky, slightly soft focus, not overly polished, not cinematic. --ar 16:9 --style raw --s 15 --v 6 --no CGI, AI look, overly perfect composition, hyperreal, HDR, oversaturated colors, cartoon, illustration, text, logo, urban background
```

##### 상황별 장면 선택 기준

| 주제 | 장면 방향 |
|------|---------|
| Acoustic Indie Pop | sunlit meadow or countryside path, open and airy |
| Folk Soul / 위로 | gentle hillside or lakeside at golden hour |
| Jazz-hop 감성 | outdoor cafe terrace with garden, warm afternoon |
| 봄/여름 | wildflower field or coastal cliff with green grass |
| 가을 / 따뜻한 노을 | golden farmland or leaf-covered countryside road |

---

##### 배경 주제 분류 기준

여러 배경 주제를 혼동할 경우 아래 기준으로 적용 섹션을 결정한다.

| 핵심 요소 | 적용 섹션 |
|---------|---------|
| 건물, 도로, 거리, 도시 구조, 낮 시간대 (실사) | 도시배경 |
| 노을, 야간 스카이라인, 강 반사, 다리, 도시 조명 중심 (실사, 인물 없음) | 도시야경 |
| 바다, 해변, 휴양, 계절감 (실사, 인물 없음) | 여름 |
| 커피, 실내 공간, 테이블, 창가, 음악 소품 (실사) | 카페 |
| 파란 하늘, 구름, 배경 여백, 청량한 공기감 (실사) | 하늘 |
| 책상, 책, 노트북, 필기구, 학습, 집중 분위기 (실사) | 공부 |
| 인물의 감정, 청춘 영화 장면, R&B 무드 (실사) | 하이틴 |
| 도로, 자연 경관, 주행 시점, 이동감 (실사) | 드라이브 |
| 들판, 자연, 온기, 피크닉, 골든아워, 야외 평온 (실사) | 어쿠스틱팝 |
| 손그림, 만화, 굵은 라인, 강한 색감, 음악 커버 일러스트 | Groove Hiphop |

복합 주제 처리:
- Groove Hip-hop + 자동차/도시/가을 → Groove Hiphop 기본
- Chill Hip-hop + 공부 (일러스트 요청 시) → Groove Hiphop 기본
- 해변 + 감성 R&B + 인물 → 하이틴 기본
- 도시 + 노을/야간 스카이라인 + 인물 없음 → 도시야경 기본
- 도시 + 다리 + 강 반사 → 도시야경 기본
- 도시 야경 + R&B 인물 있음 → 하이틴 기본 + 도시야경 요소 보조 추가
- 하늘이 넓은 도시 노을 → 도시야경 기본 + open sky 보조 추가
- 카페 + R&B 감성 인물 → 카페 기본 + emotional R&B mood 보조 추가
- 카페에서 공부 → 공부 기본 + cafe atmosphere 보조 추가
- 도시 위 하늘 → 도시배경 기본 + sky 보조 추가
- 해변과 하늘 → 여름 기본 + sky 보조 추가
- 창밖 하늘이 보이는 공부방 → 공부 기본 + sky view 보조 추가
- 드라이브 + 도시 야경 → 드라이브 기본 + 도시야경 요소 보조 추가
- 어쿠스틱팝 + 하늘 넓은 들판 → 어쿠스틱팝 기본 + sky 보조 추가

