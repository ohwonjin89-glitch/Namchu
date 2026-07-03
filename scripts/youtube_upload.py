# -*- coding: utf-8 -*-
"""
YouTube 영상 업로드 스크립트
사용법: python youtube_upload.py <json_params>

params:
  action: "auth_status" | "auth_start" | "upload" | "delete"
  videoPath: 업로드할 영상 파일 경로
  title: 제목
  description: 설명
  tags: ["tag1", "tag2", ...]
  channelId: 채널 ID (확인용)
  privacyStatus: "private" | "public" | "unlisted"
  madeForKids: false
  credentialsDir: client_secret.json이 있는 폴더 (기본: D:/AI Agent/Claude/yt_credentials)
  resultPath: 업로드 결과(upload_result.json) 저장 경로 (기본: statusPath와 같은
              디렉터리의 upload_result.json). 중복 실행 가드가 이 파일을 참조한다.
  forceReupload: True면 이미 업로드 완료 기록이 있어도 강제로 재업로드 (기본 False)

  action="delete" 전용 파라미터:
    videoId: 삭제할 영상의 YouTube videoId
    confirm: videoId와 정확히 동일한 값을 다시 넣어야만 실제로 삭제 실행됨
             (이중 확인 안전장치 — 불일치 시 삭제하지 않고 에러 반환)
"""
import sys, json, os, platform

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']

def _default_creds_dir():
    """credentialsDir 파라미터가 없을 때 쓸 기본 경로.
    Windows: 기존 운영 경로(D:\\AI Agent\\Claude\\yt_credentials) 유지.
    Linux 계열(WSL/RunPod/VPS): 이 스크립트가 위치한 저장소 루트의
    yt_credentials/ 를 사용한다 (.gitignore에도 이 컨벤션으로 등록되어 있음).
    """
    if platform.system() == 'Windows':
        return r'D:/AI Agent/Claude/yt_credentials'
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, 'yt_credentials')

def get_creds_dir(params):
    return params.get('credentialsDir', _default_creds_dir()).replace('/', os.sep)

def get_token_path(creds_dir, channel_key='dgm'):
    return os.path.join(creds_dir, f'token_{channel_key.lower()}.json')

def get_client_secret_path(creds_dir):
    return os.path.join(creds_dir, 'client_secret.json')

def _load_completed_upload(status_path, result_path):
    """중복 업로드 방지용: 이미 완료된 업로드 결과가 있으면 그 dict를, 없으면 None을 반환.
    result_path(전용 결과 파일)를 먼저 확인하고, 없으면 status_path 자체가
    이미 status=done + videoId를 가진 경우도 완료로 간주한다.
    """
    for path in (result_path, status_path):
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        video_id = data.get('videoId', '')
        if video_id and (data.get('status') == 'done' or data.get('success')):
            return data
    return None


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
            # - sys.executable: 'python'이 PATH에 없는 Linux 계열(WSL/RunPod/VPS)에서도
            #   현재 실행 중인 인터프리터를 그대로 재사용해 ENOENT를 피한다.
            # - creationflags(DETACHED_PROCESS 등)는 Windows 전용 인자라 Linux에서
            #   그대로 넘기면 ValueError가 발생하므로 Windows에서만 적용한다.
            script_path = os.path.abspath(__file__)
            listen_params = json.dumps({'action': '_listen', 'channelKey': channel_key})
            popen_kwargs = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
            if platform.system() == 'Windows':
                popen_kwargs['creationflags'] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs['start_new_session'] = True  # 부모(Node) 종료와 무관하게 계속 실행
            subprocess.Popen([sys.executable, script_path, listen_params], **popen_kwargs)
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

        # 비동기 모드: statusPath에 진행 상황을 기록
        status_path = params.get('statusPath', '')

        def write_status(st, prog, msg, extra=None):
            if not status_path:
                return
            data = {'status': st, 'progress': prog, 'message': msg}
            if extra:
                data.update(extra)
            try:
                with open(status_path, 'w', encoding='utf-8') as _f:
                    json.dump(data, _f, ensure_ascii=False)
            except Exception:
                pass

        # ── 중복 실행 가드 ──────────────────────────────────────
        # 2026-07-03 사고: youtube-uploader 에이전트가 시행착오 중 동일
        # playlist.mp4를 두 번 독립적으로 업로드에 성공시켜 DGM 채널에 동일
        # 영상이 2개 게시됨(qa-inspector, failType: code_bug). 이미 업로드가
        # 완료된 적이 있으면 forceReupload=True가 아닌 이상 재업로드하지 않는다.
        result_path = params.get('resultPath') or (
            os.path.join(os.path.dirname(status_path), 'upload_result.json') if status_path else ''
        )
        force_reupload = bool(params.get('forceReupload', False))
        if not force_reupload:
            existing = _load_completed_upload(status_path, result_path)
            if existing:
                video_id = existing.get('videoId', '')
                msg = f'이미 업로드 완료됨 (videoId: {video_id}), 중복 실행 방지'
                write_status('done', 100, msg, existing)
                return {'error': msg, 'videoId': video_id, 'duplicate': True}

        video_path = params.get('videoPath', '')
        if not os.path.exists(video_path):
            result = {'error': f'영상 파일 없음: {video_path}'}
            write_status('error', 0, result['error'])
            return result

        creds, err = load_credentials(creds_dir, channel_key)
        if err:
            write_status('error', 0, err)
            return {'error': err}
        if not creds or not creds.valid:
            msg = '인증이 필요합니다. 먼저 auth_start를 실행하세요'
            write_status('error', 0, msg)
            return {'error': msg}

        title       = params.get('title', 'Playlist | 플레이리스트')
        description = params.get('description', '')
        tags        = params.get('tags', [])
        privacy     = params.get('privacyStatus', 'private')
        kids        = params.get('madeForKids', False)
        thumbnail   = params.get('thumbnailPath', '')
        synthetic   = params.get('containsSyntheticMedia', True)

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
                'containsSyntheticMedia': synthetic,
            }
        }

        try:
            write_status('running', 5, f'YouTube API 연결 중... ({os.path.basename(video_path)})')
            youtube = build('youtube', 'v3', credentials=creds)
            # chunksize 32MB로 증가 → 청크 수 감소, 업로드 속도 향상
            media = MediaFileUpload(video_path, mimetype='video/mp4',
                                    resumable=True, chunksize=32 * 1024 * 1024)
            request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

            file_size = os.path.getsize(video_path)
            write_status('running', 10, f'업로드 시작... (파일 크기: {file_size // (1024*1024)}MB)')

            response = None
            while response is None:
                upload_status, response = request.next_chunk()
                if upload_status:
                    pct = int(upload_status.progress() * 90) + 10  # 10~100% 범위
                    uploaded_mb = int(file_size * upload_status.progress() / (1024 * 1024))
                    total_mb = file_size // (1024 * 1024)
                    write_status('running', pct,
                                 f'업로드 중... {uploaded_mb}MB / {total_mb}MB ({pct}%)')

            video_id = response.get('id', '')
            write_status('running', 95, f'영상 처리 중... (videoId: {video_id})')

            # 썸네일 업로드
            if thumbnail and os.path.exists(thumbnail):
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail)
                    ).execute()
                except Exception:
                    pass

            result = {
                'success': True,
                'videoId': video_id,
                'videoUrl': f'https://youtu.be/{video_id}',
                'studioUrl': f'https://studio.youtube.com/video/{video_id}/edit',
            }
            # 중복 실행 가드가 다음 호출에서 참조할 전용 결과 파일 기록
            if result_path:
                try:
                    with open(result_path, 'w', encoding='utf-8') as _rf:
                        json.dump(result, _rf, ensure_ascii=False)
                except Exception:
                    pass
            write_status('done', 100, f'업로드 완료! https://youtu.be/{video_id}', result)
            return result

        except googleapiclient.errors.HttpError as e:
            msg = f'YouTube API 오류: {e}'
            write_status('error', 0, msg)
            return {'error': msg}
        except Exception as e:
            msg = str(e)
            write_status('error', 0, msg)
            return {'error': msg}

    # ── 영상 삭제 (2026-07-04: 중복 업로드 사고 수습용으로 추가) ──
    # videoId와 confirm(동일 videoId 재입력)이 정확히 일치해야만 실행되는
    # 이중 확인 안전장치. 잘못된 videoId를 실수로 삭제하는 사고를 막기 위함.
    elif action == 'delete':
        from googleapiclient.discovery import build
        import googleapiclient.errors
        video_id = params.get('videoId', '')
        confirm = params.get('confirm', '')
        if not video_id:
            return {'error': 'videoId가 필요합니다'}
        if confirm != video_id:
            return {'error': f'안전장치: confirm 파라미터에 videoId({video_id})를 정확히 똑같이 넣어야 삭제가 실행됩니다'}
        creds, err = load_credentials(creds_dir, channel_key)
        if err:
            return {'error': err}
        if not creds or not creds.valid:
            # creds=None으로 build()를 호출하면 googleapiclient가 Application Default
            # Credentials를 찾다가 처리되지 않은 예외(DefaultCredentialsError)를 던진다.
            # upload 액션과 동일하게 여기서 명확한 에러로 먼저 걸러낸다.
            return {'error': '인증이 필요합니다. 먼저 auth_start를 실행하세요'}
        try:
            youtube = build('youtube', 'v3', credentials=creds)
            youtube.videos().delete(id=video_id).execute()
            return {'success': True, 'deletedVideoId': video_id}
        except googleapiclient.errors.HttpError as e:
            return {'error': f'삭제 실패: {e}'}

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
