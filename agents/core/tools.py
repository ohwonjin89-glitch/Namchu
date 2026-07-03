"""API wrappers: Suno, image (NB2), video (make-video), YouTube upload."""
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

API_BASE = os.environ.get("SUNO_API_BASE", "http://172.28.32.1:3000")


def _post(path: str, body: dict, timeout: int = 60) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(API_BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url: str, dest: str, timeout: int = 300):
    urllib.request.urlretrieve(url, dest)


def _slugify(title: str, fallback: str) -> str:
    """노래 제목 → 파일명 슬러그. 빈 제목이면 fallback(예: track_01) 사용."""
    import re
    slug = re.sub(r"[^a-z0-9_]+", "_", title.strip().lower()).strip("_")
    return slug or fallback


# ── Trend ──────────────────────────────────────────────────────────────────

def get_trend_data() -> dict:
    try:
        return _get("/api/trend-cache")
    except Exception as e:
        print(f"  트렌드 캐시 조회 실패: {e}")
        return {}


# ── Music ──────────────────────────────────────────────────────────────────

SUNO_MODEL = "chirp-fenix"  # Suno V5.5


def generate_music(concept: dict, output_dir: str) -> dict:
    """Call Suno API, poll until complete, download MP3."""
    body = {
        "prompt": concept.get("lyrics", concept.get("guide", "")),
        "tags": concept.get("style", "Korean chill pop"),
        "title": concept.get("title", "감성 플레이리스트"),
        "make_instrumental": concept.get("instrumental", False),
        "model": SUNO_MODEL,
        "wait_audio": False
    }
    result = _post("/api/custom_generate", body, timeout=30)
    if not result or not isinstance(result, list):
        raise RuntimeError(f"Suno 응답 오류: {result}")

    song_ids = [s["id"] for s in result]
    print(f"  Suno 생성 시작: {song_ids}")

    DONE = {"complete", "streaming"}
    ERROR = {"error", "failed"}

    for i in range(120):  # 20 min max
        time.sleep(10)
        try:
            ids_param = urllib.parse.quote(",".join(song_ids))
            songs = _get(f"/api/get?ids={ids_param}", timeout=60)

            # 완료된 곡 먼저 찾기 (2곡 중 1곡만 완료돼도 사용)
            for song in songs:
                status = song.get("status", "")
                audio_url = song.get("audio_url", "")
                if status in DONE and audio_url and "None" not in audio_url:
                    music_path = os.path.join(output_dir, "music.mp3")
                    _download(audio_url, music_path)
                    print(f"  Suno 완료: {song.get('title', '')} (상태: {status})")
                    return {
                        "path": music_path,
                        "ids": song_ids,
                        "title": song.get("title", "")
                    }

            # 전체 에러 상태 확인 — 모두 실패면 빠른 종료
            statuses = [s.get("status", "") for s in songs]
            if all(st in ERROR for st in statuses):
                raise RuntimeError(f"Suno 전체 곡 생성 실패: {statuses}")

            if i % 6 == 0:
                print(f"  Suno 대기 중... {statuses}")
        except RuntimeError:
            raise
        except Exception as _poll_err:
            if i % 6 == 0:
                print(f"  Suno 폴링 재시도 ({_poll_err})")

    raise RuntimeError("Suno 음악 생성 타임아웃 (20분)")


def _generate_track_ab(concept: dict, output_dir: str, track_num: int) -> dict:
    """Generate one track: submit 2 versions (A/B), poll, download, pick best."""
    body = {
        "prompt": concept.get("lyrics", concept.get("guide", "")),
        "tags": concept.get("style", "Korean chill pop"),
        "title": concept.get("title", "감성 플레이리스트"),
        "make_instrumental": concept.get("instrumental", False),
        "model": SUNO_MODEL,
        "wait_audio": False
    }
    # 초기 요청 최대 3회 재시도 (서버 busy / 일시 타임아웃 대비)
    result = None
    for attempt in range(3):
        try:
            result = _post("/api/custom_generate", body, timeout=60)
            if result and isinstance(result, list) and len(result) >= 2:
                break
        except Exception as e:
            print(f"  트랙 {track_num} 제출 재시도 {attempt+1}/3: {e}")
            time.sleep(5)
    if not result or not isinstance(result, list) or len(result) < 2:
        raise RuntimeError(f"Suno 응답 오류 (트랙 {track_num}): {result}")

    id_a, id_b = result[0]["id"], result[1]["id"]
    print(f"  트랙 {track_num} 생성 시작: A={id_a} B={id_b}")

    DONE = {"complete", "streaming"}
    ERROR = {"error", "failed"}
    url_a = url_b = ""

    for i in range(120):
        time.sleep(10)
        try:
            ids_param = urllib.parse.quote(f"{id_a},{id_b}")
            songs = _get(f"/api/get?ids={ids_param}", timeout=60)
            for j, song in enumerate(songs[:2]):
                status = song.get("status", "")
                audio_url = song.get("audio_url", "")
                if status in DONE and audio_url and "None" not in audio_url:
                    if j == 0:
                        url_a = audio_url
                    else:
                        url_b = audio_url
            if url_a and url_b:
                break
            statuses = [s.get("status", "") for s in songs[:2]]
            if all(st in ERROR for st in statuses):
                raise RuntimeError(f"트랙 {track_num} 전체 실패: {statuses}")
            if i % 6 == 0:
                print(f"  트랙 {track_num} 대기 중... {statuses}")
        except RuntimeError:
            raise
        except Exception as _poll_err:
            # HTTP timeout / 일시 오류는 재시도, 치명적 오류가 아님
            if i % 6 == 0:
                print(f"  트랙 {track_num} 폴링 재시도 ({_poll_err})")

    if not url_a and not url_b:
        raise RuntimeError(f"트랙 {track_num} 생성 타임아웃 (20분)")

    selected_dir = os.path.join(output_dir, "selected")
    os.makedirs(selected_dir, exist_ok=True)

    path_a = path_b = None
    if url_a:
        path_a = os.path.join(output_dir, f"track_{track_num:02d}_A.mp3")
        _download(url_a, path_a)
    if url_b:
        path_b = os.path.join(output_dir, f"track_{track_num:02d}_B.mp3")
        _download(url_b, path_b)

    # Pick larger file as proxy for quality
    if path_a and path_b:
        size_a = os.path.getsize(path_a)
        size_b = os.path.getsize(path_b)
        selected_path = path_a if size_a >= size_b else path_b
        selected_id = id_a if size_a >= size_b else id_b
        method = "auto_size"
    elif path_a:
        selected_path, selected_id, method = path_a, id_a, "auto_only_a"
    else:
        selected_path, selected_id, method = path_b, id_b, "auto_only_b"

    slug = _slugify(concept.get("title", ""), f"track_{track_num:02d}")
    dest = os.path.join(selected_dir, f"{slug}.mp3")
    if os.path.exists(dest):
        # 같은 concept를 공유하는 배치 호출이라 제목이 중복될 수 있음 — track_num으로 구분
        dest = os.path.join(selected_dir, f"{slug}_{track_num:02d}.mp3")
    import shutil as _shutil
    _shutil.copy2(selected_path, dest)

    size_mb = round(os.path.getsize(dest) / 1_048_576, 2)
    print(f"  트랙 {track_num} 완료: {os.path.basename(dest)} ({size_mb} MB)")

    info = {
        "trackNum": track_num,
        "title": concept.get("title", ""),
        "promptFinal": body["prompt"],
        "tagsFinal": body["tags"],
        "idA": id_a,
        "idB": id_b,
        "selectedId": selected_id,
        "selectionMethod": method,
        "selectedReason": "larger file size selected automatically",
        "qualityWarnings": [] if size_mb >= 1.0 else ["file_size_under_1mb"],
        "durationSec": None,
        "fileSizeMB": size_mb
    }
    info_path = os.path.join(output_dir, f"track_{track_num:02d}_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return {"path": dest, "info": info}


def generate_music_batch(concept: dict, output_dir: str, num_tracks: int = 20) -> dict:
    """Generate num_tracks songs in batch. Each track: 2 versions → pick 1.
    Returns dict with 'music_path' (concatenated) and 'music_info'."""
    mode = "test" if num_tracks <= 5 else "production"
    print(f"\n[music-generator] 배치 생성 시작: {num_tracks}곡 ({mode} 모드)")

    tracks = []
    failed = 0
    for n in range(1, num_tracks + 1):
        try:
            result = _generate_track_ab(concept, output_dir, n)
            tracks.append(result["info"])
            tracks[-1]["_path"] = result["path"]
        except Exception as e:
            print(f"  트랙 {n} 실패: {e}")
            failed += 1

    success_count = len(tracks)
    if success_count == 0:
        raise RuntimeError("배치 생성 완전 실패: 성공한 트랙 없음")
    if success_count < num_tracks * 0.7:
        raise RuntimeError(
            f"배치 생성 실패: 목표 {num_tracks}곡 중 {success_count}곡만 완성 (70% 미달)"
        )

    track_paths = [t["_path"] for t in tracks]
    music_path = concatenate_audio(track_paths, os.path.join(output_dir, "music.mp3"))

    import datetime
    music_info = {
        "totalTracks": success_count,
        "mode": mode,
        "tracks": [{k: v for k, v in t.items() if k != "_path"} for t in tracks],
        "finalFile": "music.mp3",
        "totalDurationSec": None,
        "generatedAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    info_path = os.path.join(output_dir, "music_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(music_info, f, ensure_ascii=False, indent=2)

    print(f"\n[music-generator] 완료: {success_count}곡 → {music_path}")
    return {"music_path": music_path, "music_info": music_info}


def concatenate_audio(track_paths: list, output_path: str) -> str:
    """Concatenate multiple MP3 files into one using FFmpeg."""
    import subprocess

    ffmpeg_cmd = None
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    if not ffmpeg_cmd:
        for ff in ["ffmpeg", "ffmpeg.exe"]:
            try:
                subprocess.run([ff, "-version"], capture_output=True, timeout=5)
                ffmpeg_cmd = ff
                break
            except Exception:
                pass
    if not ffmpeg_cmd:
        raise RuntimeError("FFmpeg를 찾을 수 없습니다.")

    concat_list = output_path.replace("music.mp3", "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in track_paths:
            f.write(f"file '{p}'\n")

    # 주의: 소스 트랙들의 비트레이트/샘플레이트가 서로 다르면 "-c copy" 스트림 복사는
    # 프레임을 그대로 이어 붙이기만 해서 출력 파일의 Xing/평균비트레이트 헤더가 실제 내용과
    # 어긋난다. 이 경우 ffprobe 등이 "invalid concatenated file detected"로 판단해
    # 파일 크기 기반으로 길이를 추정하면서 실제보다 훨씬 긴 길이(예: 642초 실제 → 1005초로 오추정)를
    # 보고하게 된다. 재인코딩하면 단일하고 정확한 헤더를 가진 파일이 생성된다.
    cmd = [
        ffmpeg_cmd, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "48000",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat 실패:\n{result.stderr[-800:]}")

    size_mb = round(os.path.getsize(output_path) / 1_048_576, 2)
    print(f"  오디오 연결 완료: {output_path} ({size_mb} MB)")
    return output_path


# ── Image ──────────────────────────────────────────────────────────────────

# 레퍼런스 폴더 → 키워드 매핑
# 스크립트 위치(agents/core/의 조부모 디렉토리) 기준으로 저장소 루트를 스스로
# 찾는다 — WSL/RunPod/VPS 등 배포 서버가 바뀌어도 하드코딩 없이 항상 정확.
_REF_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".claude", "agents", "reference",
)
_REF_KEYWORD_MAP = [
    (["cafe", "카페", "coffee", "cozy indoor", "latte"],        "카페/카페 감성사진.jpg"),
    (["terrace", "outdoor cafe"],                               "카페/카페 테라스 감성사진.jpg"),
    (["champagne", "wine", "drink"],                            "카페/샴페인.jpg"),
    (["city", "urban", "neon", "downtown"],                     "도시배경/도시야경.jpg"),
    (["new york", "뉴욕", "manhattan"],                         "도시배경/뉴욕감성.jpg"),
    (["park", "daytime city"],                                  "도시배경/뉴욕 공원.jpg"),
    (["r&b", "감성", "emotional", "film", "cinematic night"],   "감성R&B/영화감성.jpg"),
    (["insta", "aesthetic", "street portrait"],                 "감성R&B/인스타감성.jpg"),
    (["teen", "youth", "fresh", "bright cheerful"],             "감성R&B/하이틴_1.png"),
    (["hip hop", "groove", "hiphop", "vibrant", "energetic"],   "Groove hiphop/그루브_1.png"),
    (["summer", "beach", "해변", "ocean", "sea"],               "여름/해변가.jpg"),
    (["coastal", "drive", "road trip", "해안"],                 "여름/해안도로.jpg"),
    (["pool", "수영장"],                                        "여름/수영장.jpg"),
    (["study", "focus", "book", "공부", "집중"],                "공부/책.jpg"),
]


def _select_reference(prompt: str) -> tuple[str | None, str | None]:
    """Keyword-match reference image. Returns (abs_path, rel_name) or (None, None)."""
    pl = prompt.lower()
    for keywords, rel in _REF_KEYWORD_MAP:
        if any(k in pl for k in keywords):
            full = f"{_REF_BASE}/{rel}"
            if os.path.exists(full):
                return full, rel
    return None, None


# Unsplash CDN 사진 ID 목록 — 대시보드 PHOTOS 배열 기반 (API 키 불필요)
# URL: https://images.unsplash.com/photo-{id}?w=1920&h=1080&fit=crop&auto=format
_UNSPLASH_PHOTO_MAP: dict = {
    "cafe": [
        "1554118811-1e0d58224f24",  # woman cafe warm
        "1495474472287-4d71bcdd2085",  # coffee window morning
        "1481349518771-20055b2a7b24",  # reading cafe vintage
        "1509042239860-f550ce710b93",  # cozy indoor light
        "1442512595331-e89e73853f31",  # alone emotional cafe
        "1501339847302-ac426a4a7cbb",  # coffee morning light
        "1508739773434-c26b3d09e071",  # film cafe emotion
        "1559305616-3f99cd43e353",  # korean aesthetic cafe
    ],
    "night": [
        "1467269204519-bf7b702a32b2",
        "1519120944692-1a8d8cfc107f",
        "1444703686981-a3abbc4d4fe3",
        "1519681393784-d120267933ba",
        "1531219572328-a0171b4448a3",
    ],
    "drive": [
        "1449824913935-59a10b8d2000",
        "1545558014-8692077e9b5c",
        "1485163819542-3d5b2fa11b40",
        "1506905925346-21bda4d32df4",
    ],
    "travel": [
        "1469854523086-cc02fe5d8800",
        "1488646953014-85cb44e25828",
        "1476514525535-07fb3b4ae5f1",
        "1452421822248-d4c2b47f0c81",
    ],
    "rainy": [
        "1515705576963-95cad62945b6",
        "1509315307596-f9b10a9ddaf6",
        "1519682577862-22b62b24cb73",
        "1534274988757-a79023d7f947",
    ],
    "summer": [
        "1507525428034-b723cf961d3e",
        "1476231682828-37e571bc172f",
        "1502680390469-be75c86b636f",
        "1505118380757-91f5f5632de0",
    ],
    "study": [
        "1456735190827-d1262f71b8a3",
        "1507842217343-583bb7270b66",
        "1513475382585-d06e58bcb0e0",
        "1497633762265-9d179a990aa6",
    ],
    "urban": [
        "1477959858617-67f85cf4f1df",
        "1444084686090-f06a8a29e43e",
        "1486325212027-8081e485255e",
        "1555952517-2e8e729e0960",
    ],
    "nature": [
        "1441974231531-c6227db76b6e",
        "1418065460487-3e41a6c84dc5",
        "1501854140801-50d01698950b",
        "1448375240586-882707db888b",
    ],
    "emotion": [
        "1521017432531-fbd92d768814",
        "1544005313-94ddf0286df2",
        "1508214751196-bcfd4ca60f91",
    ],
}

_UNSPLASH_THEME_KEYWORDS = [
    (["cafe", "카페", "coffee", "cozy", "latte", "espresso"],           "cafe"),
    (["night", "새벽", "midnight", "late night", "dark city", "dim"],   "night"),
    (["drive", "드라이브", "highway", "road trip", "car window"],       "drive"),
    (["travel", "여행", "wander", "vacation", "trip", "scenic"],        "travel"),
    (["rain", "비", "rainy", "window rain", "storm", "wet street"],     "rainy"),
    (["summer", "여름", "beach", "ocean", "sea", "coastal", "pool"],    "summer"),
    (["study", "공부", "focus", "책", "book", "library", "desk"],       "study"),
    (["city", "urban", "도시", "neon", "downtown", "metropolitan"],     "urban"),
    (["nature", "자연", "forest", "mountain", "green", "landscape"],    "nature"),
    (["emotion", "감성", "portrait", "feeling", "mood", "cinematic"],   "emotion"),
]


def _fetch_copyright_free(prompt: str, dest: str) -> bool:
    """Download a theme-matched Unsplash photo via CDN (API 키 불필요)."""
    import random as _rand
    pl = prompt.lower()
    theme = "cafe"  # 기본값
    for keywords, t in _UNSPLASH_THEME_KEYWORDS:
        if any(k in pl for k in keywords):
            theme = t
            break

    photo_ids = _UNSPLASH_PHOTO_MAP.get(theme, _UNSPLASH_PHOTO_MAP["cafe"])
    photo_id = _rand.choice(photo_ids)
    url = f"https://images.unsplash.com/photo-{photo_id}?w=1920&h=1080&fit=crop&auto=format"
    try:
        _download(url, dest, timeout=30)
        size = os.path.getsize(dest) if os.path.exists(dest) else 0
        print(f"  Unsplash CDN: theme={theme} id={photo_id} ({round(size/1024)}KB)")
        return size > 100_000
    except Exception as e:
        print(f"  Unsplash CDN 실패: {e}")
        return False


def generate_image(prompt: str, output_dir: str) -> str:
    """
    3단계 이미지 생성:
      1) 저작권프리 (loremflickr) — 병렬 시작
      2) Midjourney AI — 레퍼런스 sref 포함
      3) 두 결과 비교 → 파일 크기 기준 최적안 선택
    image_info.json에 전 과정 기록.
    """
    import base64 as _b64
    os.makedirs(output_dir, exist_ok=True)

    mj_path  = os.path.join(output_dir, "candidate_mj.jpg")
    cf_path  = os.path.join(output_dir, "candidate_cf.jpg")
    dest     = os.path.join(output_dir, "background.jpg")
    info: dict = {
        "promptFinal": prompt,
        "referenceUsed": None,
        "referenceFile": None,
        "mjCandidates": [],
        "source": None,
        "fallbackUsed": False,
        "fallbackReason": "",
        "cfKeywords": None,
        "qualityCheck": {"fileExists": False, "fileSizeKB": 0},
        "warnings": [],
    }

    # ── Step 1: 저작권프리 병렬 시작 (백그라운드 스레드) ───────────────────
    import threading
    cf_ok = [False]
    def _cf_worker():
        cf_ok[0] = _fetch_copyright_free(prompt, cf_path)
    cf_thread = threading.Thread(target=_cf_worker, daemon=True)
    cf_thread.start()

    # ── Step 2: 레퍼런스 이미지 선택 ──────────────────────────────────────
    ref_path, ref_rel = _select_reference(prompt)
    sref_b64 = []
    if ref_path:
        try:
            with open(ref_path, "rb") as f:
                sref_b64 = [_b64.b64encode(f.read()).decode()]
            info["referenceUsed"] = ref_path
            info["referenceFile"] = ref_rel
            print(f"  레퍼런스 선택: {ref_rel}")
        except Exception as e:
            info["warnings"].append(f"reference load failed: {e}")

    # ── Step 3: Midjourney 생성 ────────────────────────────────────────────
    mj_ok = False
    mj_all_urls: list[str] = []
    try:
        mj_body: dict = {
            "prompt": prompt,
            "noPrompt": "text, logo, watermark, people, face, signature",
            "ar": "16:9",
            "stylize": 100,
            "quality": 1,
            "speed": "fast",
        }
        if sref_b64:
            mj_body["srefBase64"] = sref_b64

        result = _post("/api/midjourney", mj_body, timeout=360)
        images = result.get("images", [])

        # URL 추출 — 문자열 또는 {"url":...} 객체 모두 처리
        for img in images:
            url = img if isinstance(img, str) else (
                img.get("url") or img.get("imageUrl") or img.get("image_url") or "")
            if url:
                mj_all_urls.append(url)

        info["mjCandidates"] = mj_all_urls

        if mj_all_urls:
            _download(mj_all_urls[0], mj_path)
            mj_ok = os.path.exists(mj_path) and os.path.getsize(mj_path) > 50_000
            print(f"  Midjourney 완료: {len(mj_all_urls)}장 생성 → candidate_mj.jpg ({round(os.path.getsize(mj_path)/1024)}KB)")
    except Exception as e:
        info["warnings"].append(f"midjourney: {e}")
        print(f"  Midjourney 실패: {e}")

    # ── Step 4: 저작권프리 결과 대기 ──────────────────────────────────────
    cf_thread.join(timeout=35)
    import re as _re2
    cf_keywords = _re2.findall(r'[a-zA-Z]{4,}', prompt)
    info["cfKeywords"] = ",".join(cf_keywords[:4])
    if cf_ok[0]:
        cf_size = os.path.getsize(cf_path)
        print(f"  저작권프리 완료: candidate_cf.jpg ({round(cf_size/1024)}KB) [loremflickr · {info['cfKeywords']}]")
    else:
        print("  저작권프리 실패 또는 크기 미달")

    # ── Step 5: 최적안 선택 ───────────────────────────────────────────────
    import shutil as _sh
    mj_size = os.path.getsize(mj_path) if mj_ok and os.path.exists(mj_path) else 0
    cf_size = os.path.getsize(cf_path) if cf_ok[0] and os.path.exists(cf_path) else 0

    if mj_size >= 200_000:          # MJ 200KB 이상이면 우선
        _sh.copy2(mj_path, dest)
        info["source"] = "midjourney"
        print(f"  ✅ 선택: Midjourney ({round(mj_size/1024)}KB) > 저작권프리 ({round(cf_size/1024)}KB)")
    elif cf_size > mj_size:
        _sh.copy2(cf_path, dest)
        info["source"] = "copyright_free"
        print(f"  ✅ 선택: 저작권프리 ({round(cf_size/1024)}KB) > Midjourney ({round(mj_size/1024)}KB)")
    elif mj_size > 0:
        _sh.copy2(mj_path, dest)
        info["source"] = "midjourney"
        print(f"  ✅ 선택: Midjourney ({round(mj_size/1024)}KB)")
    elif cf_size > 0:
        _sh.copy2(cf_path, dest)
        info["source"] = "copyright_free"
        print(f"  ✅ 선택: 저작권프리 ({round(cf_size/1024)}KB)")
    else:
        # 3차 폴백: 단색
        info["fallbackUsed"] = True
        info["fallbackReason"] = "MJ and copyright-free both failed"
        dest = _fallback_image(output_dir)
        info["source"] = "fallback"
        print("  ⚠️ 모두 실패 → 단색 배경 사용")

    # image_info.json 저장
    if os.path.exists(dest):
        info["qualityCheck"]["fileExists"] = True
        info["qualityCheck"]["fileSizeKB"] = round(os.path.getsize(dest) / 1024)
    info_path = os.path.join(output_dir, "image_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return dest

    # ── 3차: 단색 그라디언트 폴백 ─────────────────────────────────────────
    return _fallback_image(output_dir)


def _fallback_image(output_dir: str) -> str:
    """Create a simple dark gradient image using only stdlib."""
    import struct, zlib

    dest = os.path.join(output_dir, "background.png")
    w, h = 1920, 1080

    raw = []
    for y in range(h):
        row = b"\x00"
        for x in range(w):
            r = max(10, 30 - int(30 * y / h))
            g = max(10, 20 - int(10 * y / h))
            b_val = max(30, 60 - int(30 * y / h))
            row += bytes([r, g, b_val])
        raw.append(row)

    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    raw_bytes = b"".join(raw)
    compressed = zlib.compress(raw_bytes, 6)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    with open(dest, "wb") as f:
        f.write(png)
    return dest


# ── Video ──────────────────────────────────────────────────────────────────

def _to_win(path: str) -> str:
    """Convert WSL /mnt/c/ path to Windows C:\\ path."""
    if path.startswith("/mnt/c/"):
        return "C:\\" + path[7:].replace("/", "\\")
    if path.startswith("/mnt/"):
        parts = path[5:].split("/", 1)
        drive = parts[0].upper() + ":\\"
        rest = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return drive + rest
    return path


def _to_wsl(path: str) -> str:
    """Convert Windows C:\\ path to WSL /mnt/c/ path."""
    if len(path) >= 3 and path[1] == ":" and path[2] in ("\\""/"):
        drive = path[0].lower()
        rest = path[3:].replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return path


def create_video(music_path: str, image_path: str,
                 output_dir: str, title: str = "") -> str:
    """Create video via /api/make-video, with FFmpeg direct fallback."""
    import shutil

    win_output_dir = _to_win(output_dir)
    video_filename = "playlist.mp4"

    # Copy inputs to Korean-free temp paths so Windows Python (make_video.py) can access them
    safe_dir = "/mnt/c/temp_dgm_upload"
    os.makedirs(safe_dir, exist_ok=True)
    img_ext = os.path.splitext(image_path)[1] or ".jpg"
    safe_image = os.path.join(safe_dir, f"background{img_ext}")
    safe_music = os.path.join(safe_dir, "music.mp3")
    try:
        shutil.copy2(image_path, safe_image)
        shutil.copy2(music_path, safe_music)
    except Exception as e:
        print(f"  temp 복사 실패, 원본 경로 사용: {e}")
        safe_image = image_path
        safe_music = music_path

    win_music = _to_win(safe_music)
    win_image = _to_win(safe_image)

    body = {
        "bgImagePath": win_image,
        "audioPath": win_music,
        "bgImageUrl": win_image,
        "musicFiles": [{"path": win_music, "title": title or "track"}],
        "musicDir": win_output_dir,
        "outputDir": win_output_dir,
        "outputFileName": video_filename,
        "texts": [{
            "content": title or "감성 플레이리스트",
            "text": title or "감성 플레이리스트",
            "fontFamily": "맑은 고딕",
            "fontSize": 52,
            "color": "#FFFFFF",
            "leftPct": 5, "topPct": 80,
            "widthPct": 90, "heightPct": 10,
            "bold": True, "shadow": False
        }],
        "textOverlays": [{
            "text": title or "감성 플레이리스트",
            "fontFamily": "맑은 고딕",
            "fontSize": 52,
            "color": "#FFFFFF",
            "leftPct": 5, "topPct": 80,
            "widthPct": 90, "heightPct": 10,
            "bold": True
        }]
    }

    try:
        result = _post("/api/make-video", body, timeout=60)
        task_id = result.get("taskId", "")

        if task_id:
            print(f"  영상 제작 중 (taskId: {task_id})...")
            for i in range(90):  # 15 min max
                time.sleep(10)
                try:
                    enc = urllib.parse.quote(task_id)
                    poll = _get(f"/api/make-video?taskId={enc}")
                    status = poll.get("status", "")
                    progress = poll.get("progress", 0)
                    if i % 3 == 0:
                        print(f"  진행: {progress}%")
                    if status == "done":
                        out_path = poll.get("outputPath", "")
                        if out_path:
                            return out_path
                    elif status == "error":
                        msg = poll.get("message", "unknown error")
                        print(f"  make-video API 오류: {msg} → FFmpeg 폴백")
                        break  # fall through to ffmpeg fallback
                except Exception:
                    pass
            # Fall through to FFmpeg fallback
    except Exception as e:
        print(f"  /api/make-video 실패: {e} → FFmpeg 직접 생성 시도")

    # ── FFmpeg 직접 생성 폴백 ─────────────────────────────────────────────
    return _create_video_ffmpeg(music_path, image_path, output_dir, title, video_filename)


def _create_video_ffmpeg(music_path: str, image_path: str,
                         output_dir: str, title: str, filename: str = "playlist.mp4") -> str:
    """Fallback: create video directly with bundled FFmpeg (imageio-ffmpeg)."""
    import subprocess
    video_path = os.path.join(output_dir, filename)

    # Get ffmpeg binary path
    ffmpeg_cmd = None
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"  imageio-ffmpeg 사용: {ffmpeg_cmd}")
    except ImportError:
        pass

    if not ffmpeg_cmd:
        for ff in ["ffmpeg", "ffmpeg.exe"]:
            try:
                subprocess.run([ff, "-version"], capture_output=True, timeout=5)
                ffmpeg_cmd = ff
                break
            except Exception:
                pass

    if not ffmpeg_cmd:
        raise RuntimeError(
            "FFmpeg를 찾을 수 없습니다. "
            "'python3 -m pip install imageio-ffmpeg --break-system-packages'로 설치하세요."
        )

    # Escape special chars in title for drawtext
    safe_title = title.replace("'", "").replace('"', "").replace(":", "").replace("\\", "")[:50]

    cmd = [
        ffmpeg_cmd, "-y",
        "-loop", "1", "-i", image_path,
        "-i", music_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080",
        "-shortest",
        video_path
    ]

    print(f"  FFmpeg 영상 생성 중...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 실패:\n{result.stderr[-800:]}")

    print(f"  영상 생성 완료: {video_path}")
    return video_path


# ── Upload ─────────────────────────────────────────────────────────────────

def upload_youtube(video_path: str, title: str,
                   description: str, tags: list,
                   channel_key: str = "DGM") -> dict:
    win_path = _to_win(video_path)

    # Copy to a path without Korean characters so Windows can access it
    import shutil
    safe_dir = "/mnt/c/temp_dgm_upload"
    os.makedirs(safe_dir, exist_ok=True)
    safe_linux_path = os.path.join(safe_dir, "upload.mp4")
    safe_win_path = "C:\\temp_dgm_upload\\upload.mp4"
    # video_path may be a Windows path (from make-video API); convert to WSL for copy
    linux_video_path = _to_wsl(video_path) if video_path[1:3] == ":\\" else video_path
    try:
        shutil.copy2(linux_video_path, safe_linux_path)
        win_path = safe_win_path
        print(f"  업로드용 임시 복사: {safe_linux_path}")
    except Exception as e:
        print(f"  파일 복사 실패, 원본 경로 사용: {e}")

    body = {
        "action": "upload",
        "channelKey": channel_key,
        "videoPath": win_path,
        "title": title,
        "description": description,
        "tags": tags,
        "privacyStatus": "private",
        "madeForKids": False
    }
    return _post("/api/youtube-upload", body, timeout=600)
