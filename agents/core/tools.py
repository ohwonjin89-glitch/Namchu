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

    DONE = {"complete", "streaming"}
    ERROR = {"error", "failed"}

    for i in range(120):  # 20 min max
        time.sleep(10)
        try:
            ids_param = urllib.parse.quote(",".join(song_ids))
            songs = _get(f"/api/get?ids={ids_param}")

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
        except (RuntimeError, TimeoutError):
            raise
        except Exception:
            pass

    raise TimeoutError("Suno 음악 생성 타임아웃 (20분)")


# ── Image ──────────────────────────────────────────────────────────────────

def generate_image(prompt: str, output_dir: str) -> str:
    """Call NB2 image API; fallback to solid-colour image if unavailable."""
    result = _post("/api/nano-banana",
                   {"prompt": prompt, "size": "16:9", "quality": "2K"},
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
    try:
        shutil.copy2(video_path, safe_linux_path)
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
