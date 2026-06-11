# -*- coding: utf-8 -*-
"""
YouTube 영상 업로드 스크립트
사용법: python youtube_upload.py <json_params>

params:
  action: "auth_status" | "auth_start" | "upload"
  videoPath: 업로드할 영상 파일 경로
  title: 제목
  description: 설명
  tags: ["tag1", "tag2", ...]
  channelId: 채널 ID (확인용)
  privacyStatus: "private" | "public" | "unlisted"
  madeForKids: false
  credentialsDir: client_secret.json이 있는 폴더 (기본: D:/AI Agent/Claude/yt_credentials)
"""
import sys, json, os

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']

def get_creds_dir(params):
    return params.get('credentialsDir', r'D:/AI Agent/Claude/yt_credentials').replace('/', os.sep)

def get_token_path(creds_dir, channel_key='dgm'):
    return os.path.join(creds_dir, f'token_{channel_key}.json')

def get_client_secret_path(creds_dir):
    return os.path.join(creds_dir, 'client_secret.json')

def load_credentials(creds_dir, channel_key='dgm'):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    token_path = get_token_path(creds_dir, channel_key)
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
        except Exception as e:
            return None, f'토큰 갱신 실패: {e}'
    return creds, None

def run(params):
    action = params.get('action', 'auth_status')
    creds_dir = get_creds_dir(params)
    channel_key = params.get('channelKey', 'dgm')
    os.makedirs(creds_dir, exist_ok=True)

    # ── 인증 상태 확인 ────────────────────────────────────
    if action == 'auth_status':
        secret_path = get_client_secret_path(creds_dir)
        token_path = get_token_path(creds_dir, channel_key)
        has_secret = os.path.exists(secret_path)
        has_token = os.path.exists(token_path)
        if not has_secret:
            return {'status': 'no_credentials', 'message': 'client_secret.json 없음'}
        if not has_token:
            return {'status': 'no_token', 'message': '인증 필요'}
        creds, err = load_credentials(creds_dir, channel_key)
        if err or not creds or not creds.valid:
            return {'status': 'expired', 'message': '토큰 만료 — 재인증 필요'}
        return {'status': 'ok', 'message': '인증됨'}

    # ── OAuth2 인증 시작: URL 반환 + 백그라운드 리스너 ──────
    elif action == 'auth_start':
        import subprocess, secrets, hashlib, base64
        from google_auth_oauthlib.flow import InstalledAppFlow
        secret_path = get_client_secret_path(creds_dir)
        if not os.path.exists(secret_path):
            return {'error': f'client_secret.json을 {creds_dir}에 넣어주세요'}
        try:
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            flow.redirect_uri = 'http://localhost:8095/'
            # PKCE code verifier 생성 (Google Desktop App 필수)
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('ascii')).digest()
            ).rstrip(b'=').decode('ascii')
            auth_url, state = flow.authorization_url(
                prompt='consent', access_type='offline',
                code_challenge=code_challenge, code_challenge_method='S256'
            )
            # 상태 + code_verifier 저장 (리스너에서 사용)
            pending_path = os.path.join(creds_dir, 'yt_auth_pending.json')
            with open(pending_path, 'w', encoding='utf-8') as f:
                json.dump({'state': state, 'channelKey': channel_key, 'codeVerifier': code_verifier}, f)
            # 백그라운드 리스너 시작 (분리된 프로세스)
            script_path = os.path.abspath(__file__)
            listen_params = json.dumps({'action': '_listen', 'channelKey': channel_key})
            flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                ['python', script_path, listen_params],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=flags
            )
            return {'status': 'pending', 'authUrl': auth_url}
        except Exception as e:
            return {'error': str(e)}

    # ── 백그라운드 콜백 리스너 (auth_start 에서 서브프로세스로 실행) ──
    elif action == '_listen':
        import http.server, urllib.parse
        from google_auth_oauthlib.flow import InstalledAppFlow
        secret_path = get_client_secret_path(creds_dir)
        pending_path = os.path.join(creds_dir, 'yt_auth_pending.json')
        try:
            with open(pending_path, encoding='utf-8') as f:
                pending = json.load(f)
        except Exception:
            return None
        ch_key = pending.get('channelKey', channel_key)
        code_result = [None]

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                code = params.get('code', [None])[0]
                if code:
                    code_result[0] = code
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                msg = '✅ 인증 완료! 이 탭을 닫고 대시보드로 돌아가세요.' if code else '❌ 코드 없음'
                self.wfile.write(f'<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:50px;background:#fdf6ed"><h1 style="color:#5c3d1e">{msg}</h1></body></html>'.encode('utf-8'))
            def log_message(self, *a): pass

        srv = http.server.HTTPServer(('localhost', 8095), _Handler)
        srv.timeout = 600
        srv.handle_request()
        srv.server_close()
        if not code_result[0]:
            return None
        try:
            code_verifier = pending.get('codeVerifier', '')
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            flow.redirect_uri = 'http://localhost:8095/'
            flow.code_verifier = code_verifier  # PKCE verifier 전달
            flow.fetch_token(code=code_result[0])
            token_path = get_token_path(creds_dir, ch_key)
            with open(token_path, 'w', encoding='utf-8') as f:
                f.write(flow.credentials.to_json())
            try: os.remove(pending_path)
            except: pass
        except Exception as e:
            err_path = os.path.join(creds_dir, 'yt_auth_error.txt')
            with open(err_path, 'w', encoding='utf-8') as ef:
                ef.write(str(e))
        return None

    # ── 업로드 ────────────────────────────────────────────
    elif action == 'upload':
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import googleapiclient.errors

        video_path = params.get('videoPath', '')
        if not os.path.exists(video_path):
            return {'error': f'영상 파일 없음: {video_path}'}

        creds, err = load_credentials(creds_dir, channel_key)
        if err:
            return {'error': err}
        if not creds or not creds.valid:
            return {'error': '인증이 필요합니다. 먼저 auth_start를 실행하세요'}

        title       = params.get('title', 'Playlist | AI 생성 음악')
        description = params.get('description', '')
        tags        = params.get('tags', [])
        privacy     = params.get('privacyStatus', 'private')
        kids        = params.get('madeForKids', False)
        thumbnail   = params.get('thumbnailPath', '')

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '10',  # Music category
                'defaultLanguage': 'ko',
                'defaultAudioLanguage': 'ko',
            },
            'status': {
                'privacyStatus': privacy,
                'madeForKids': kids,
                'selfDeclaredMadeForKids': kids,
            }
        }

        try:
            youtube = build('youtube', 'v3', credentials=creds)
            media = MediaFileUpload(video_path, mimetype='video/mp4',
                                    resumable=True, chunksize=5 * 1024 * 1024)
            request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()

            video_id = response.get('id', '')

            # 썸네일 업로드
            if thumbnail and os.path.exists(thumbnail):
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail)
                    ).execute()
                except Exception:
                    pass

            return {
                'success': True,
                'videoId': video_id,
                'videoUrl': f'https://youtu.be/{video_id}',
                'studioUrl': f'https://studio.youtube.com/video/{video_id}/edit',
            }
        except googleapiclient.errors.HttpError as e:
            return {'error': f'YouTube API 오류: {e}'}
        except Exception as e:
            return {'error': str(e)}

    return {'error': f'알 수 없는 action: {action}'}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'params JSON 필요'}))
        sys.exit(1)
    try:
        params = json.loads(sys.argv[1])
        result = run(params)
    except Exception as e:
        result = {'error': str(e)}
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
