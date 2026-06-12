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


# ── Trend ──────────────────────────────────────────────────────────────────

def get_trend_data() -> dict:
    try:
        return _get("/api/trend-cache")
    except Exception as e:
        print(f"  트렌드 캐시 조회 실패: {e}")
        return {}


# ── Music ──────────────────────────────────────────────────────────────────

def generate_music(concept: dict, output_dir: str) -> dict:
    """Call Suno API, poll until complete, download MP3."""
    body = {
        "prompt": concept.get("lyrics", concept.get("guide", "")),
        "tags": concept.get("style", "Korean chill pop"),
        "title": concept.get("title", "감성 플레이리스트"),
        "make_instrumental": concept.get("instrumental", False),
        "wait_audio": False
    }
    result = _post("/api/custom_generate", body, timeout=30)
    if not result or not isinstance(result, list):
        raise RuntimeError(f"Suno 응답 오류: {result}")

    song_ids = [s["id"] for s in result]
    print(f"  Suno 생성 시작: {song_ids}")

    for _ in range(72):  # 12 min max
        time.sleep(10)
        try:
            ids_param = urllib.parse.quote(",".join(song_ids))
            songs = _get(f"/api/get?ids={ids_param}")
            if all(s.get("status") in ("complete", "streaming") for s in songs):
                audio_url = songs[0].get("audio_url", "")
                if audio_url:
                    music_path = os.path.join(output_dir, "music.mp3")
                    _download(audio_url, music_path)
                    return {
                        "path": music_path,
                        "ids": song_ids,
                        "title": songs[0].get("title", "")
                    }
        except Exception:
            pass

    raise TimeoutError("Suno 음악 생성 타임아웃 (12분)")


# ── Image ──────────────────────────────────────────────────────────────────

def generate_image(prompt: str, output_dir: str) -> str:
    """Call NB2 image API; fallback to solid-colour image if unavailable."""
    result = _post("/api/nano-banana",
                   {"prompt": prompt, "size": "1792x1024", "quality": "hd"},
                   timeout=60)

    task_id = result.get("taskId", "")
    image_url = result.get("imageUrl", "")

    if task_id and not image_url:
        for _ in range(30):
            time.sleep(10)
            try:
                enc = urllib.parse.quote(task_id)
                poll = _get(f"/api/nano-banana?taskId={enc}")
                if poll.get("status") == "done":
                    image_url = poll.get("imageUrl", "")
                    break
            except Exception:
                pass

    dest = os.path.join(output_dir, "background.jpg")
    if image_url:
        _download(image_url, dest)
        return dest

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

def create_video(music_path: str, image_path: str,
                 output_dir: str, title: str = "") -> str:
    """Call /api/make-video, poll until complete."""
    win_output_dir = output_dir.replace("/mnt/c/", "C:/").replace("/", "\\")

    body = {
        "bgImagePath": image_path,
        "audioPath": music_path,
        "outputDir": win_output_dir,
        "texts": [{
            "content": title or "감성 플레이리스트",
            "fontFamily": "맑은 고딕",
            "fontSize": 52,
            "color": "#FFFFFF",
            "leftPct": 5, "topPct": 80,
            "widthPct": 90, "heightPct": 10,
            "bold": True, "shadow": False
        }],
        "spectrum": {
            "enabled": True,
            "color": "#A78BFA",
            "leftPct": 5, "topPct": 88,
            "widthPct": 90, "heightPct": 8
        },
        "watermark": {
            "enabled": True,
            "text": "@DGM_Playlist",
            "position": "bottomRight"
        }
    }

    result = _post("/api/make-video", body, timeout=60)
    task_id = result.get("taskId", "")
    if not task_id:
        # Synchronous response
        video_path = result.get("outputPath", "")
        if video_path:
            return video_path
        raise RuntimeError(f"영상 제작 실패: {result}")

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
                video_path = poll.get("outputPath", "")
                if video_path:
                    return video_path
        except Exception:
            pass

    raise TimeoutError("영상 제작 타임아웃 (15분)")


# ── Upload ─────────────────────────────────────────────────────────────────

def upload_youtube(video_path: str, title: str,
                   description: str, tags: list,
                   channel_key: str = "DGM") -> dict:
    body = {
        "action": "upload",
        "channelKey": channel_key,
        "videoPath": video_path,
        "title": title,
        "description": description,
        "tags": tags,
        "privacyStatus": "private",
        "madeForKids": False
    }
    return _post("/api/youtube-upload", body, timeout=600)
