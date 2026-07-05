"""
╔══════════════════════════════════════════════════════════════╗
║         Playlisttann · 유튜브 영상 자동 제작 스크립트           ║
╚══════════════════════════════════════════════════════════════╝

사용 방법 (CLI):
  python make_video.py DGM_Playlist 테스트영상
  python make_video.py Playlisttann 카페음악
  python make_video.py DGM_Playlist 테스트영상 --logo white
  python make_video.py DGM_Playlist 테스트영상 --logo black

사용 방법 (API 모드 - 대시보드에서 호출):
  python make_video.py --config <config.json 경로>

로고 자동 선택:
  밝은 배경 → 검은 로고(logo_Black.png)
  어두운 배경 → 하얀 로고(logo_White.png)

폴더 구조:
  channels\\
  ├── Playlisttann\\
  │   ├── assets\\        ← logo_Black.png, logo_White.png
  │   └── projects\\
  │       └── 카페음악_20260605\\
  │           ├── music\\, background\\, output\\
  └── DGM_Playlist\\
      ├── assets\\        ← logo_Black.png, logo_White.png
      └── projects\\
"""

import os
import sys
import glob
import platform
import subprocess
import json
import tempfile
import urllib.request
import re
import unicodedata
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"

BASE_DIR   = r"D:\AI Agent\Claude"
CHANNELS_DIR = os.path.join(BASE_DIR, "channels")
if IS_WINDOWS:
    FFMPEG_PATH  = r"D:\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
    FFPROBE_PATH = r"D:\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe"
else:
    # RunPod 서버(Linux): 시스템 PATH의 ffmpeg/ffprobe 사용 (apt로 설치됨)
    FFMPEG_PATH  = "ffmpeg"
    FFPROBE_PATH = "ffprobe"
VALID_CHANNELS = ["Playlisttann", "DGM_Playlist"]

def get_video_codec_args(crf=23):
    return ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf)]


_CHROMA_KEY_CACHE = {}

def detect_chroma_key_color(video_path, fallback='0x00FF00'):
    """그린스크린 영상의 실제 배경색을 코너 픽셀에서 샘플링해 반환.
    스펙트럼 에셋마다 그린스크린 톤이 미묘하게 달라(예: 0x039700, 0x0CAF05) 0x00FF00으로
    고정하면 chromakey가 거의 안 먹거나(너무 엄격) 반대로 흰 막대까지 같이 지워지는(너무 느슨)
    문제가 있었음 — 실제 픽셀을 읽어서 그 영상에 맞는 키 컬러를 쓴다."""
    if video_path in _CHROMA_KEY_CACHE:
        return _CHROMA_KEY_CACHE[video_path]
    color = fallback
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-y', '-i', video_path, '-vf', 'crop=4:4:0:0',
             '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
            capture_output=True, timeout=15
        )
        data = result.stdout
        if len(data) >= 3:
            r, g, b = data[0], data[1], data[2]
            color = f'0x{r:02X}{g:02X}{b:02X}'
    except Exception:
        pass
    _CHROMA_KEY_CACHE[video_path] = color
    return color


# ── 배경 밝기 분석 ──────────────────────────────────────────────

def get_background_brightness(image_path):
    """배경사진 평균 밝기 반환 (0=완전검정 ~ 255=완전흰색)"""
    try:
        from PIL import Image
        img = Image.open(image_path).convert("L")  # 흑백으로 변환
        # 중앙 영역만 샘플링 (가장자리 제외)
        w, h = img.size
        crop = img.crop((w//4, h//4, w*3//4, h*3//4))
        pixels = list(crop.getdata())
        return sum(pixels) / len(pixels)
    except ImportError:
        return None  # PIL 없으면 None 반환


def select_logo(channel, bg_image_path, manual_override=None):
    """
    로고 파일 선택
    - manual_override: 'black' 또는 'white' (대시보드/명령어에서 지정)
    - None이면 배경 밝기로 자동 선택
    """
    assets_dir = os.path.join(CHANNELS_DIR, channel, "assets")
    logo_black = os.path.join(assets_dir, "logo_Black.png")
    logo_white = os.path.join(assets_dir, "logo_White.png")

    has_black = os.path.exists(logo_black)
    has_white = os.path.exists(logo_white)

    # 둘 다 없으면 None
    if not has_black and not has_white:
        return None, "로고 없음 (배경에 로고 포함된 경우)"

    # 수동 지정
    if manual_override == "black" and has_black:
        return logo_black, "수동 지정 → 검은 로고"
    if manual_override == "white" and has_white:
        return logo_white, "수동 지정 → 하얀 로고"

    # 자동 감지
    brightness = get_background_brightness(bg_image_path)

    if brightness is None:
        # PIL 없을 때 → 기본값 화이트 로고
        logo = logo_white if has_white else logo_black
        return logo, "PIL 미설치 → 기본값 하얀 로고"

    if brightness > 128:
        # 밝은 배경 → 검은 로고
        logo = logo_black if has_black else logo_white
        color = "검은"
    else:
        # 어두운 배경 → 하얀 로고
        logo = logo_white if has_white else logo_black
        color = "하얀"

    return logo, f"자동 감지 (밝기 {brightness:.0f}) → {color} 로고"


# ── 파일 유틸 ───────────────────────────────────────────────────

def get_or_create_project(channel, project_name):
    if len(project_name) > 9 and project_name[-9] == '_' and project_name[-8:].isdigit():
        folder_name = project_name
    else:
        today = datetime.now().strftime("%Y%m%d")
        folder_name = f"{project_name}_{today}"
    project_path = os.path.join(CHANNELS_DIR, channel, "projects", folder_name)
    for sub in ["music", "background", "output"]:
        os.makedirs(os.path.join(project_path, sub), exist_ok=True)
    return project_path, folder_name


def get_music_files(music_folder):
    files = []
    for ext in ['*.mp3', '*.wav', '*.m4a', '*.flac']:
        files.extend(glob.glob(os.path.join(music_folder, ext)))
    files.sort(key=lambda x: os.path.basename(x).lower())
    return files


def get_background_image(background_folder):
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        found = glob.glob(os.path.join(background_folder, ext))
        if found:
            return found[0]
    return None


def get_audio_duration(filepath):
    cmd = [FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json', '-show_streams', filepath]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if 'duration' in stream:
                return float(stream['duration'])
    except:
        pass
    return 180.0


# ── 영상 제작 ───────────────────────────────────────────────────

def make_video(channel, project_path, folder_name, logo_override=None):

    music_folder      = os.path.join(project_path, "music")
    background_folder = os.path.join(project_path, "background")
    output_folder     = os.path.join(project_path, "output")

    print("\n" + "="*60)
    print(f"  채널: {channel}  |  프로젝트: {folder_name}")
    print("="*60)

    music_files = get_music_files(music_folder)
    if not music_files:
        print(f"\n❌ music 폴더에 음악 파일이 없어요: {music_folder}")
        return False

    bg_image = get_background_image(background_folder)
    if not bg_image:
        print(f"\n❌ background 폴더에 사진이 없어요: {background_folder}")
        return False

    # 로고 선택
    logo_path, logo_reason = select_logo(channel, bg_image, logo_override)

    print(f"\n  🖼️  배경사진: {os.path.basename(bg_image)}")
    print(f"  🎨 로고: {logo_reason}")

    print(f"\n📂 음악 {len(music_files)}곡:")
    total_duration = 0
    for i, f in enumerate(music_files, 1):
        dur = get_audio_duration(f)
        total_duration += dur
        print(f"  {i:02d}. {os.path.basename(f)} ({int(dur//60)}:{int(dur%60):02d})")

    total_mins, total_secs = int(total_duration // 60), int(total_duration % 60)
    print(f"\n  ⏱ 총 재생시간: {total_mins}분 {total_secs}초")
    if total_duration < 3000:
        print(f"  ⚠️  1시간보다 짧아요 ({total_mins}분)")

    # concat 파일
    concat_file = os.path.join(tempfile.gettempdir(), "_playlist_concat.txt")
    with open(concat_file, 'w', encoding='utf-8') as f:
        for mf in music_files:
            f.write(f"file '{os.path.abspath(mf).replace(chr(92), '/')}'\n")

    channel_tag = "playlisttann" if channel == "Playlisttann" else "dgm_playlist"
    output_file = os.path.join(output_folder, f"{folder_name}_{channel_tag}.mp4")

    # FFmpeg 명령어 구성
    print("\n🎬 영상 제작 중...")

    if logo_path:
        # 배경 + 로고 합성 (로고 중앙 배치)
        cmd = [
            FFMPEG_PATH, '-y',
            '-loop', '1', '-i', bg_image,
            '-loop', '1', '-i', logo_path,
            '-f', 'concat', '-safe', '0', '-i', concat_file,
            '-filter_complex',
            '[0]scale=1920:1080[bg];'
            '[1]scale=480:-1:flags=lanczos,format=rgba,'
            "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='min(255,max(0,(lum(X,Y)-180)*255/75))'[logo];"
            '[bg][logo]overlay=(W-w)/2:(H-h)/2:format=auto[v]',
            '-map', '[v]', '-map', '2:a',
            *get_video_codec_args(23),
            '-r', '30',
            '-c:a', 'aac', '-b:a', '320k', '-ar', '44100',
            '-shortest', output_file
        ]
    else:
        # 로고 없음 (배경에 이미 로고 포함)
        cmd = [
            FFMPEG_PATH, '-y',
            '-loop', '1', '-i', bg_image,
            '-f', 'concat', '-safe', '0', '-i', concat_file,
            *get_video_codec_args(23),
            '-vf', 'scale=1920:1080', '-r', '30',
            '-c:a', 'aac', '-b:a', '320k', '-ar', '44100',
            '-shortest', output_file
        ]

    print(f"  출력: {output_file}")
    process = subprocess.run(cmd)

    if os.path.exists(concat_file):
        os.remove(concat_file)

    if process.returncode == 0:
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"\n✅ 완료! 채널: {channel}")
        print(f"   파일: {output_file}")
        print(f"   크기: {size_mb:.1f} MB  |  길이: {total_mins}분 {total_secs}초")
        return True
    else:
        print(f"\n❌ 오류 발생 (returncode: {process.returncode})")
        return False


# ── 프로젝트 목록 ───────────────────────────────────────────────

def list_projects():
    print("\n현재 프로젝트 목록:")
    for channel in VALID_CHANNELS:
        projects_dir = os.path.join(CHANNELS_DIR, channel, "projects")
        print(f"\n  📺 {channel}")
        if not os.path.exists(projects_dir):
            print("    (없음)")
            continue
        projects = [d for d in os.listdir(projects_dir)
                    if os.path.isdir(os.path.join(projects_dir, d))]
        if not projects:
            print("    (없음)")
        for p in sorted(projects):
            path = os.path.join(projects_dir, p)
            music_count = len(glob.glob(os.path.join(path, "music", "*.mp3")))
            has_output  = len(glob.glob(os.path.join(path, "output", "*.mp4"))) > 0
            status = "✅ 완성" if has_output else f"🎵 음악 {music_count}곡"
            print(f"    • {p}  [{status}]")


# ── API 모드 (대시보드에서 --config 로 호출) ─────────────────────────

def write_api_status(output_dir, status, progress, message, output_path=None):
    data = {"status": status, "progress": progress, "message": message}
    if output_path:
        data["outputPath"] = output_path
    print(json.dumps(data, ensure_ascii=False), flush=True)
    try:
        with open(os.path.join(output_dir, "_status.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def download_image(url, dest_path):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        with open(dest_path, "wb") as f:
            f.write(response.read())


def normalize_title(s):
    s = re.sub(r"\s*\(\d+\)$", "", s)
    return s.replace("⭐", "").replace("★", "").strip().lower()


def get_ordered_audio_files(music_dir, song_titles=None):
    if not os.path.isdir(music_dir):
        return []
    all_files = sorted(f for f in os.listdir(music_dir) if f.lower().endswith(".mp3"))
    if not song_titles:
        return [os.path.join(music_dir, f) for f in all_files]
    matched, used = [], set()
    for title in song_titles:
        norm = normalize_title(title)
        for f in all_files:
            if f in used:
                continue
            ft = re.sub(r"^\d+_", "", re.sub(r"\.mp3$", "", f, flags=re.IGNORECASE))
            if normalize_title(ft) == norm:
                matched.append(os.path.join(music_dir, f))
                used.add(f)
                break
    for f in all_files:
        if f not in used:
            matched.append(os.path.join(music_dir, f))
    return matched


if IS_WINDOWS:
    _FONT_DIR = r'D:/AI Agent/Claude/fonts'
else:
    # Linux 계열(RunPod/VPS 등): 배포 서버마다 프로젝트 루트 경로가 다르므로
    # (RunPod=/workspace/suno-api, VPS=/home/dgm/suno-api 등) 하드코딩 대신
    # 이 스크립트 위치 기준으로 <프로젝트 루트>/assets/fonts를 자동으로 찾는다.
    # 폰트 파일 자체는 서버별로 scp로 미리 복사해둬야 한다.
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _FONT_DIR = os.path.join(_PROJECT_ROOT, 'assets', 'fonts')

if IS_WINDOWS:
    FONT_MAP = {
        # ── Pretendard (D:\AI Agent\Claude\fonts\) ─────────────────────
        'pretendard':            f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'pretendard regular':    f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'pretendard light':      f'{_FONT_DIR}/Pretendard-Light.ttf',
        'pretendard medium':     f'{_FONT_DIR}/Pretendard-Medium.ttf',
        'pretendard semibold':   f'{_FONT_DIR}/Pretendard-SemiBold.ttf',
        'pretendard bold':       f'{_FONT_DIR}/Pretendard-Bold.ttf',
        'pretendard extrabold':  f'{_FONT_DIR}/Pretendard-ExtraBold.ttf',
        'pretendard black':      f'{_FONT_DIR}/Pretendard-Black.ttf',
        # ── 시스템 폰트 ─────────────────────────────────────────────────
        'noto sans kr':          r'C:/Windows/Fonts/NotoSansKR-VF.ttf',
        'noto serif kr':         r'C:/Windows/Fonts/NotoSerifKR-VF.ttf',
        'malgun gothic':         r'C:/Windows/Fonts/malgun.ttf',
        'malgun bold':           r'C:/Windows/Fonts/malgunbd.ttf',
        # 대시보드 한글 레이블 그대로 (fontLabel 값이 한글이므로 exact match 위해 추가)
        '맑은 고딕':              r'C:/Windows/Fonts/malgun.ttf',
        '맑은 고딕 bold':         r'C:/Windows/Fonts/malgunbd.ttf',
        'arial':                 r'C:/Windows/Fonts/arial.ttf',
        'segoe ui':              r'C:/Windows/Fonts/segoeui.ttf',
    }
else:
    # Linux 서버에는 Windows 시스템 폰트(맑은 고딕 등)가 없으므로
    # 모든 라벨을 Pretendard 굵기로 매핑해 동일한 키로 폴백시킨다.
    FONT_MAP = {
        'pretendard':            f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'pretendard regular':    f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'pretendard light':      f'{_FONT_DIR}/Pretendard-Light.ttf',
        'pretendard medium':     f'{_FONT_DIR}/Pretendard-Medium.ttf',
        'pretendard semibold':   f'{_FONT_DIR}/Pretendard-SemiBold.ttf',
        'pretendard bold':       f'{_FONT_DIR}/Pretendard-Bold.ttf',
        'pretendard extrabold':  f'{_FONT_DIR}/Pretendard-ExtraBold.ttf',
        'pretendard black':      f'{_FONT_DIR}/Pretendard-Black.ttf',
        'noto sans kr':          f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'noto serif kr':         f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'malgun gothic':         f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'malgun bold':           f'{_FONT_DIR}/Pretendard-Bold.ttf',
        '맑은 고딕':              f'{_FONT_DIR}/Pretendard-Regular.ttf',
        '맑은 고딕 bold':         f'{_FONT_DIR}/Pretendard-Bold.ttf',
        'arial':                 f'{_FONT_DIR}/Pretendard-Regular.ttf',
        'segoe ui':              f'{_FONT_DIR}/Pretendard-Regular.ttf',
    }
DEFAULT_FONT = f'{_FONT_DIR}/Pretendard-Regular.ttf'


def _css_color_to_ffmpeg(css_color):
    """css color string (rgb(r,g,b) or #rrggbb) → FFmpeg 0xRRGGBB"""
    import re
    css_color = css_color.strip()
    m = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', css_color)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"0x{r:02X}{g:02X}{b:02X}"
    hex_c = css_color.lstrip('#')
    if len(hex_c) == 6:
        return f"0x{hex_c.upper()}"
    return "0xFFFFFF"


def build_video_filter(bg_idx, audio_idx, logo_idx, spec_idx, VW, VH,
                        logo_w_px, overlay_x, logo_v_pos, logo_opacity,
                        spectrum_cfg, text_overlays, preview_w, preview_h):
    """
    동적으로 FFmpeg filter_complex 문자열을 생성한다.
    반환: (filter_complex_str, output_video_label)
    """
    parts  = []
    cur    = 'bg_s'
    # lum() 대신 직접 수식 사용 (FFmpeg 8.x에서 lum() 미지원)
    _lum = "(0.2126*r(X,Y)+0.7152*g(X,Y)+0.0722*b(X,Y))"
    alpha_lum = f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='min(255,max(0,({_lum}-180)*255/75))'"

    # 1. 배경 스케일
    parts.append(
        f"[{bg_idx}:v]scale={VW}:{VH}:force_original_aspect_ratio=decrease,"
        f"pad={VW}:{VH}:(ow-iw)/2:(oh-ih)/2[{cur}]"
    )

    # 2. 로고 오버레이 (PNG 원본 알파채널 사용, geq 불필요)
    if logo_idx is not None:
        op_f = f",colorchannelmixer=aa={logo_opacity:.2f}" if logo_opacity < 0.99 else ""
        parts.append(
            f"[{logo_idx}:v]scale={logo_w_px}:-1:flags=lanczos,"
            f"format=rgba{op_f}[logo_o]"
        )
        nxt = 'v_logo'
        parts.append(
            f"[{cur}][logo_o]overlay={overlay_x}:"
            f"main_h-overlay_h-{logo_v_pos}*main_h/100:format=auto[{nxt}]"
        )
        cur = nxt

    # 3. 스펙트럼 오버레이
    # 대시보드에서 설정한 위치(leftPct/topPct)·크기(widthPct/heightPct)로 배치
    if spec_idx is not None and spectrum_cfg:
        op   = float(spectrum_cfg.get('opacity', 1.0))
        op_f = f",colorchannelmixer=aa={op:.2f}" if op < 0.99 else ""
        fp   = spectrum_cfg.get('filePath', '')
        # 대시보드 element 크기·위치 → 영상 픽셀 좌표 변환
        sw = max(1, int(VW * spectrum_cfg.get('widthPct',  40) / 100))
        sh = max(1, int(VH * spectrum_cfg.get('heightPct', 40) / 100))
        sx = max(0, int(VW * spectrum_cfg.get('leftPct',    5) / 100))
        sy = max(0, int(VH * spectrum_cfg.get('topPct',    70) / 100))
        # 스펙트럼 에셋은 흰색 바만 제공됨 — color='black' 요청 시 negate로 색만 반전 (알파 유지)
        neg_f = ",negate=negate_alpha=0" if spectrum_cfg.get('color', 'white') == 'black' else ""
        _has_alpha = False
        if fp.lower().endswith('.webm'):
            try:
                _r = subprocess.run(
                    [FFPROBE_PATH, '-v', 'error', '-show_streams', '-select_streams', 'v:0',
                     '-of', 'json', fp], capture_output=True, text=True
                )
                import json as _json
                _pf = _json.loads(_r.stdout).get('streams', [{}])[0].get('pix_fmt', '')
                _has_alpha = 'a' in _pf
            except Exception:
                _has_alpha = False
        if _has_alpha:
            parts.append(
                f"[{spec_idx}:v]scale={sw}:{sh}:flags=lanczos,"
                f"format=yuva420p{neg_f}{op_f}[spec_o]"
            )
        else:
            # tolerance(0~255, 기본 80)를 chromakey similarity로 변환.
            # 기존엔 단순 /255 였는데(80 → 0.314) 이러면 흰색 막대까지 같이 키 아웃되어
            # 스펙트럼이 통째로 안 보이는 사고가 있었음 — 0.02~0.18 안전 범위로 재매핑.
            tol = max(0, min(255, spectrum_cfg.get('tolerance', 80)))
            sim = max(0.02, min(0.18, (tol / 255) * 0.45))
            key_color = detect_chroma_key_color(fp)
            # 원본 해상도에서 먼저 크로마키 처리 후 축소해야 가장자리가 깨끗하게 빠진다.
            # (축소 먼저 하면 그린 배경색이 인접 픽셀과 섞여 경계에 초록 잔상/흐림이 남음)
            parts.append(
                f"[{spec_idx}:v]chromakey={key_color}:{sim:.3f}:0.1,format=rgba{neg_f},"
                f"scale={sw}:{sh}:flags=lanczos{op_f}[spec_o]"
            )
        nxt = 'v_spec'
        parts.append(f"[{cur}][spec_o]overlay={sx}:{sy}:format=auto:eof_action=repeat[{nxt}]")
        cur = nxt

    # 4. 텍스트 오버레이 (drawtext)
    pw = preview_w or 500
    ph = preview_h or 281
    sx_scale = VW / pw
    sy_scale = VH / ph
    font_scale = (sx_scale + sy_scale) / 2

    for i, ot in enumerate(text_overlays or []):
        txt = ot.get('text', '').strip()
        if not txt or txt == '텍스트 입력':
            continue
        # 𝐏𝐥𝐚𝐲𝐥𝐢𝐬𝐭 같은 유니코드 굵은체 등 호환 문자를 일반 글자로 변환
        # (로컬 폰트가 Mathematical Alphanumeric Symbols 글리프를 지원하지 않아 □로 깨짐)
        txt = unicodedata.normalize('NFKC', txt)
        x_px = max(0, int(ot.get('leftPct', 10) / 100 * VW))
        y_px = max(0, int(ot.get('topPct',  10) / 100 * VH))
        fs   = max(12, int(ot.get('fontSize', 24) * font_scale))
        ff_color = _css_color_to_ffmpeg(ot.get('color', '#ffffff'))
        alpha    = max(0.0, min(1.0, float(ot.get('opacity', 1.0))))
        font_label = ot.get('fontLabel', '').lower()
        fam        = ot.get('fontFamily', '').lower()
        font_f     = DEFAULT_FONT
        if font_label:
            # 정확한 키 매칭 (substring 사용 시 'pretendard'가 'pretendard bold' 전에 매칭되는 버그 방지)
            font_f = FONT_MAP.get(font_label, DEFAULT_FONT)
        else:
            for key, fp in FONT_MAP.items():
                if key in fam:
                    font_f = fp
                    break
        # 텍스트: 싱글쿼트 내부에서 특수문자 이스케이프
        safe_txt = (txt.replace('\\', '\\\\')
                       .replace("'", "\\'")
                       .replace('%', '\\%'))
        # 알파는 fontcolor에 포함 (0xRRGGBBAA 형식)
        alpha_hex = hex(round(alpha * 255))[2:].upper().zfill(2)
        fc = f"{ff_color}{alpha_hex}"
        # Windows 경로의 콜론을 FFmpeg 필터 구문에 맞게 이스케이프 (C: → C\:)
        font_f_escaped = font_f.replace(':', '\\:')
        dt = (f"drawtext=text='{safe_txt}'"
              f":fontfile='{font_f_escaped}'"
              f":x={x_px}:y={y_px}"
              f":fontsize={fs}"
              f":fontcolor={fc}")
        nxt = f'v_txt{i}'
        parts.append(f"[{cur}]{dt}[{nxt}]")
        cur = nxt

    # 인코더 입력 전 픽셀 포맷 강제 (yuvj420p full-range 방지)
    nxt = 'final_v'
    parts.append(f"[{cur}]format=yuv420p[{nxt}]")
    cur = nxt

    return ';'.join(parts), cur


def run_api_mode(config_path):
    """대시보드 API 모드: config JSON을 읽어 영상 제작 후 status 파일 업데이트"""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    bg_url        = cfg.get("bgImageUrl", "") or cfg.get("bgImagePath", "")
    bg_video_path = cfg.get("bgVideoPath", "")   # 동영상 배경 (신규)
    music_dir    = cfg.get("musicDir", "")
    # audioPath 단일 파일 지원 (Python 오케스트레이터용)
    _audio_path = cfg.get("audioPath", "")
    if _audio_path and not cfg.get("musicFiles"):
        cfg["musicFiles"] = [{"path": _audio_path, "title": cfg.get("outputFileName", "track").replace(".mp4","")}]
        if not music_dir:
            music_dir = os.path.dirname(_audio_path)
    music_files_cfg = cfg.get("musicFiles", [])  # [{path, title}] 우선 사용
    song_titles  = cfg.get("songTitles", [])
    logo_path    = cfg.get("logoPath", "")
    logo_color   = cfg.get("logoColor", "white")
    logo_h_pos     = int(cfg.get("logoHPos", 50))
    logo_v_pos     = int(cfg.get("logoVPos", 20))
    logo_size      = int(cfg.get("logoSize", 28))
    logo_opacity   = float(cfg.get("logoOpacity", 1.0))
    output_dir     = cfg.get("outputDir", "")
    output_name    = cfg.get("outputFileName", "output.mp4")
    # texts/spectrum/watermark 키를 textOverlays/spectrumOverlay로 변환 (Python 오케스트레이터용)
    if not cfg.get("textOverlays") and cfg.get("texts"):
        # Normalize: 'content' key → 'text' key
        text_overlays = [
            dict(ot, text=ot.get("text", ot.get("content", "")))
            for ot in cfg["texts"]
        ]
    else:
        text_overlays  = cfg.get("textOverlays", [])
    if not cfg.get("spectrumOverlay") and cfg.get("spectrum"):
        spectrum_cfg = cfg["spectrum"]
    else:
        spectrum_cfg   = cfg.get("spectrumOverlay")
    preview_w      = int(cfg.get("previewWidth",  500))
    preview_h      = int(cfg.get("previewHeight", 281))

    if (not music_dir and not music_files_cfg) or not output_dir:
        print(json.dumps({"status": "error", "progress": 0, "message": "musicDir와 outputDir가 필요합니다."}))
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # 1. 배경 처리 (동영상 또는 이미지)
    bg_path = None
    is_video_bg = bool(bg_video_path and os.path.isfile(bg_video_path))
    if is_video_bg:
        bg_path = bg_video_path
        write_api_status(output_dir, "running", 5, "배경 동영상 확인 완료")
    elif bg_url:
        bg_dir = os.path.join(os.path.dirname(output_dir.rstrip("/\\")), "background")
        os.makedirs(bg_dir, exist_ok=True)
        ext = ".jpg"
        for c in [".png", ".webp", ".jpeg"]:
            if c in bg_url.lower().split("?")[0]:
                ext = c
                break
        bg_path = os.path.join(bg_dir, "background" + ext)

        if bg_url.startswith("http"):
            write_api_status(output_dir, "running", 5, "배경 이미지 다운로드 중...")
            try:
                download_image(bg_url, bg_path)
            except Exception as e:
                write_api_status(output_dir, "error", 0, f"이미지 다운로드 실패: {e}")
                sys.exit(1)
        elif os.path.isfile(bg_url):
            # 직접 업로드된 로컬 파일 복사
            write_api_status(output_dir, "running", 5, "배경 이미지 준비 중...")
            import shutil
            shutil.copy2(bg_url, bg_path)
        else:
            write_api_status(output_dir, "error", 0, f"배경 이미지 파일을 찾을 수 없습니다: {bg_url}")
            sys.exit(1)

    # 2. 음악 파일 수집
    write_api_status(output_dir, "running", 15, "음악 파일 준비 중...")
    if music_files_cfg:
        # 대시보드에서 정확한 경로 배열을 전달한 경우 — 그대로 사용 (디렉토리 스캔 안 함)
        audio_files = [mf["path"] for mf in music_files_cfg if os.path.isfile(mf.get("path", ""))]
        if not audio_files:
            # 경로가 없거나 파일이 없으면 디렉토리 스캔 fallback
            audio_files = get_ordered_audio_files(music_dir, song_titles or None)
    else:
        audio_files = get_ordered_audio_files(music_dir, song_titles or None)
    if not audio_files:
        write_api_status(output_dir, "error", 0, f"음악 파일 없음: {music_dir}")
        sys.exit(1)

    # 3. 음악 합치기
    write_api_status(output_dir, "running", 20, f"{len(audio_files)}곡 합치는 중...")
    filelist_path  = os.path.join(output_dir, "_filelist.txt")
    combined_audio = os.path.join(output_dir, "_combined.mp3")
    with open(filelist_path, "w", encoding="utf-8") as f:
        for p in audio_files:
            f.write(f"file '{p.replace(chr(92), '/').replace(chr(39), chr(92)+chr(39))}'\n")

    r = subprocess.run(
        [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", filelist_path, "-c", "copy", combined_audio],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        write_api_status(output_dir, "error", 0, f"음악 합치기 실패: {r.stderr[-400:]}")
        sys.exit(1)

    # 4. 영상 인코딩
    # ── 화질/속도 설정 (속도 최적화 적용) ──────────────────────────
    VW, VH  = 1920, 1080  # 1080p Full HD
    FPS     = 24           # 24fps (음악 영상 표준)
    CRF     = 23           # CRF 23: 1080p 기본 화질 (YouTube 권장 수준)
    TUNE    = "stillimage" # 정적 배경 최적화 (배경 이미지일 때만)

    spec_msg = " + 스펙트럼" if spectrum_cfg else ""
    txt_msg  = f" + 텍스트 {len(text_overlays)}개" if text_overlays else ""
    write_api_status(output_dir, "running", 40, f"영상 인코딩 중{spec_msg}{txt_msg} (1080p/24fps)...")

    output_path = os.path.join(output_dir, output_name)
    logo_w_px = int(VW * logo_size / 100)
    overlay_x = max(0, int(VW * logo_h_pos / 100) - logo_w_px // 2)

    # ── 입력 목록 동적 구성 ────────────────────────────────────────
    cmd_inputs = []
    if is_video_bg:
        cmd_inputs += ["-stream_loop", "-1", "-i", bg_video_path]
    elif bg_path:
        cmd_inputs += ["-loop", "1", "-i", bg_path]
    else:
        cmd_inputs += ["-f", "lavfi", "-i", f"color=c=0x2c1810:s={VW}x{VH}:r=1"]
    bg_idx    = 0

    cmd_inputs += ["-i", combined_audio]
    audio_idx = 1
    next_idx  = 2

    logo_idx = None
    if logo_path and os.path.exists(logo_path):
        cmd_inputs += ["-i", logo_path]
        logo_idx  = next_idx; next_idx += 1

    spec_idx = None
    if spectrum_cfg and spectrum_cfg.get("filePath") and os.path.exists(spectrum_cfg["filePath"]):
        cmd_inputs += ["-stream_loop", "-1", "-an", "-i", spectrum_cfg["filePath"]]
        spec_idx  = next_idx; next_idx += 1

    # 음악 길이를 명시적으로 지정 (-shortest 대체)
    audio_duration = get_audio_duration(combined_audio)

    # ── filter_complex 생성 ────────────────────────────────────────
    filter_cx, out_label = build_video_filter(
        bg_idx, audio_idx, logo_idx, spec_idx,
        VW, VH, logo_w_px, overlay_x, logo_v_pos, logo_opacity,
        spectrum_cfg, text_overlays, preview_w, preview_h
    )

    codec_args = get_video_codec_args(CRF)
    tune_args = [] if is_video_bg else ["-tune", TUNE]

    cmd = [FFMPEG_PATH, "-y"] + cmd_inputs + [
        "-filter_complex", filter_cx,
        "-map", f"[{out_label}]", "-map", f"{audio_idx}:a",
        *codec_args,
    ] + tune_args + ["-pix_fmt", "yuv420p"] + [
        "-color_range", "1",
        "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(audio_duration),
        output_path
    ]

    # stderr를 파일로 저장하여 실제 오류 메시지 보존
    stderr_log = os.path.join(output_dir, "_ffmpeg_stderr.log")
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if r.stderr:
        with open(stderr_log, "w", encoding="utf-8") as _sf:
            _sf.write(r.stderr)
    if r.returncode != 0:
        # 오류 메시지 추출: 진행상황 로그 제외하고 실제 오류만
        err_lines = [ln.strip() for ln in r.stderr.splitlines()
                     if ln.strip() and not ln.strip().startswith("frame=") and not ln.strip().startswith("size=")]
        err_msg = "\n".join(err_lines[-15:]) if err_lines else r.stderr[-1000:]
        write_api_status(output_dir, "error", 0, f"영상 인코딩 실패: {err_msg}")
        sys.exit(1)

    # 5. 정리
    for tmp in [filelist_path, combined_audio]:
        try:
            os.remove(tmp)
        except Exception:
            pass

    write_api_status(output_dir, "done", 100, "영상 제작 완료!", output_path)


# ── 메인 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    # API 모드: python make_video.py --config <path>
    if len(sys.argv) >= 3 and sys.argv[1] == "--config":
        run_api_mode(sys.argv[2])
        sys.exit(0)

    print("╔══════════════════════════════════════╗")
    print("║   Playlisttann · 영상 자동 제작기     ║")
    print("╚══════════════════════════════════════╝\n")

    if len(sys.argv) < 3:
        print("사용법: python make_video.py [채널] [프로젝트] [--logo black|white]")
        print()
        print("  예시:")
        print("    python make_video.py DGM_Playlist 테스트영상")
        print("    python make_video.py DGM_Playlist 테스트영상 --logo white")
        print("    python make_video.py Playlisttann 카페음악   --logo black")
        print()
        list_projects()
        sys.exit(0)

    channel      = sys.argv[1]
    project_name = sys.argv[2]
    logo_override = None

    # --logo 옵션 파싱
    if "--logo" in sys.argv:
        idx = sys.argv.index("--logo")
        if idx + 1 < len(sys.argv):
            logo_override = sys.argv[idx + 1].lower()
            if logo_override not in ("black", "white"):
                print(f"❌ --logo 값은 'black' 또는 'white' 만 가능해요.")
                sys.exit(1)

    if channel not in VALID_CHANNELS:
        print(f"❌ 채널명 오류: {channel}")
        print(f"   사용 가능: {', '.join(VALID_CHANNELS)}")
        sys.exit(1)

    project_path, folder_name = get_or_create_project(channel, project_name)

    print(f"📺 채널: {channel}")
    print(f"📁 경로: {project_path}")
    print(f"   ├── music\\      ← MP3 파일")
    print(f"   ├── background\\ ← 배경사진 (로고 없는 원본)")
    print(f"   └── output\\     ← 완성 영상 저장\n")

    success = make_video(channel, project_path, folder_name, logo_override)

    if success:
        channel_tag = "playlisttann" if channel == "Playlisttann" else "dgm_playlist"
        print(f"\n🎉 유튜브 업로드 준비 완료 → {channel}")
