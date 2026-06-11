# -*- coding: utf-8 -*-
"""
YouTube 트렌드 분석 스크립트
params:
  action: "fetch_trends" | "send_kakao_report"
  apiKey: YouTube Data API v3 키
  query: 검색 키워드 (기본: "Playlist")
  minViews: 최소 조회수 (기본: 50000)
  kakaoToken: 카카오 액세스 토큰 (나에게보내기)
  days: 최근 N일 (기본: 7)
"""
import sys, json, os, datetime, urllib.request, urllib.parse

YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_VIDEO_URL  = 'https://www.googleapis.com/youtube/v3/videos'
YOUTUBE_CHANNEL_URL= 'https://www.googleapis.com/youtube/v3/channels'
KAKAO_ME_URL       = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'

# 경쟁사 채널 ID (사전 수집 완료)
RIVAL_CHANNELS = {
    'UYoung Wave':   'UCAFLHVP7O_AFTrwDy_MS9ng',
    'SISO Wave':     'UClRxY7lEeNqc6oezxGSpkKA',
    'Breeze Mood':   'UCz1OuU2oqj_FCXEhy3XnvxQ',
    'serinwave':     'UCCGzxk5MO85W0unC37f2T1Q',
    'grgr playlist': 'UCBfrb7uxrP9blQKWsdjD7dw',  # @grgr_playlist
}

def yt_api(url, params):
    full = url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

import re as _re

EXCLUDE_KEYWORDS = {'kpop', 'k-pop', '로파이', 'lo-fi', 'lofi', 'bgm'}

# 플레이리스트 채널 인정 키워드 (하나 이상이면 통과)
PLAYLIST_KW = {'playlist', '플레이리스트', '음악', '노래', '플리'}

def is_valid_title(title):
    """제목 필터: 한글 필수 + 플레이리스트 키워드 하나 이상 + 제외 키워드 없음"""
    tl = title.lower()
    has_korean    = bool(_re.search(r'[가-힣]', title))
    has_playlist  = any(kw in tl for kw in PLAYLIST_KW)
    has_excluded  = any(kw in tl for kw in EXCLUDE_KEYWORDS)
    return has_korean and has_playlist and not has_excluded

def fetch_trends(api_key, query='Playlist', days=7, min_subs=5000, max_results=50):
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

    # 1. 검색 — 4개 쿼리로 넓게 수집 후 필터링
    SEARCH_QUERIES = [
        '감성 플레이리스트',
        '카페 음악 플레이리스트',
        '새벽 감성 Playlist',
        '음악 모음 한국',
    ]
    collected_ids = {}
    for q in SEARCH_QUERIES:
        search_params = {
            'part': 'snippet', 'q': q, 'type': 'video',
            'order': 'viewCount', 'regionCode': 'KR', 'relevanceLanguage': 'ko',
            'publishedAfter': published_after, 'maxResults': max_results,
            'key': api_key
        }
        search_data = yt_api(YOUTUBE_SEARCH_URL, search_params)
        for it in search_data.get('items', []):
            vid_id = it['id'].get('videoId')
            if vid_id:
                collected_ids[vid_id] = True

    if not collected_ids:
        return []

    # 2. 영상 통계 (최대 100개 — 두 번으로 나눠 요청)
    video_ids = list(collected_ids.keys())
    vid_items = []
    for chunk_start in range(0, min(len(video_ids), 100), 50):
        chunk = video_ids[chunk_start:chunk_start+50]
        vid_params = {
            'part': 'snippet,statistics', 'id': ','.join(chunk), 'key': api_key
        }
        vid_data = yt_api(YOUTUBE_VIDEO_URL, vid_params)
        vid_items.extend(vid_data.get('items', []))

    # 3. 채널 구독자 확인
    channel_ids = list({v['snippet']['channelId'] for v in vid_items})
    ch_subs = {}
    for ch_chunk_start in range(0, len(channel_ids), 50):
        ch_chunk = channel_ids[ch_chunk_start:ch_chunk_start+50]
        ch_params = {'part': 'statistics', 'id': ','.join(ch_chunk), 'key': api_key}
        ch_data = yt_api(YOUTUBE_CHANNEL_URL, ch_params)
        for c in ch_data.get('items', []):
            ch_subs[c['id']] = int(c['statistics'].get('subscriberCount', 0))

    # 4. 필터링: 한글+플레이리스트 제목 + 구독자 기준
    results = []
    for v in vid_items:
        title      = v['snippet']['title']
        stats      = v.get('statistics', {})
        view_count = int(stats.get('viewCount', 0))
        ch_id      = v['snippet']['channelId']
        subs       = ch_subs.get(ch_id, 0)

        if not is_valid_title(title):
            continue
        if subs < min_subs:
            continue

        results.append({
            'videoId':         v['id'],
            'title':           title,
            'channelTitle':    v['snippet']['channelTitle'],
            'publishedAt':     v['snippet']['publishedAt'][:10],
            'viewCount':       view_count,
            'likeCount':       int(stats.get('likeCount', 0)),
            'commentCount':    int(stats.get('commentCount', 0)),
            'description':     v['snippet'].get('description', '')[:300],
            'tags':            v['snippet'].get('tags', [])[:10],
            'thumbnail':       v['snippet']['thumbnails'].get('medium', {}).get('url', ''),
            'url':             f'https://youtu.be/{v["id"]}',
            'subscriberCount': subs,
        })

    results.sort(key=lambda x: x['viewCount'], reverse=True)
    return results[:20]

def fetch_rivals(api_key, days=30):
    """경쟁사 채널 최근 업로드 수집 (기본: 30일 이내)"""
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
    results = []

    # 채널 통계 일괄 수집
    channel_ids = ','.join(RIVAL_CHANNELS.values())
    try:
        ch_data = yt_api(YOUTUBE_CHANNEL_URL, {
            'part': 'snippet,statistics', 'id': channel_ids, 'key': api_key
        })
        ch_map = {c['id']: c for c in ch_data.get('items', [])}
    except Exception as e:
        ch_map = {}

    for name, ch_id in RIVAL_CHANNELS.items():
        ch_info  = ch_map.get(ch_id, {})
        subs     = int(ch_info.get('statistics', {}).get('subscriberCount', 0))
        ch_title = ch_info.get('snippet', {}).get('title', name)
        try:
            # 최근 30일 이내 영상 최대 3개 검색
            search = yt_api(YOUTUBE_SEARCH_URL, {
                'part': 'snippet', 'channelId': ch_id,
                'type': 'video', 'order': 'date',
                'publishedAfter': published_after,
                'maxResults': 3, 'key': api_key
            })
            items = search.get('items', [])

            if not items:
                results.append({
                    'name': name, 'channelId': ch_id, 'channelTitle': ch_title,
                    'latestTitle': '', 'latestVideoId': '', 'latestDate': '',
                    'subscriberCount': subs, 'viewCount': 0, 'url': '',
                    'noRecent': True,
                })
                continue

            # 최신 영상 view count 가져오기
            vid_ids = [it['id']['videoId'] for it in items if it.get('id', {}).get('videoId')]
            vid_stats = {}
            if vid_ids:
                vd = yt_api(YOUTUBE_VIDEO_URL, {
                    'part': 'statistics', 'id': ','.join(vid_ids), 'key': api_key
                })
                for v in vd.get('items', []):
                    vid_stats[v['id']] = int(v['statistics'].get('viewCount', 0))

            latest = items[0]
            vid_id = latest['id'].get('videoId', '')
            title  = latest['snippet'].get('title', '')
            date   = latest['snippet'].get('publishedAt', '')[:10]
            results.append({
                'name': name, 'channelId': ch_id, 'channelTitle': ch_title,
                'latestTitle': title, 'latestVideoId': vid_id, 'latestDate': date,
                'subscriberCount': subs,
                'viewCount': vid_stats.get(vid_id, 0),
                'url': f'https://youtu.be/{vid_id}' if vid_id else '',
            })
        except Exception as e:
            results.append({
                'name': name, 'channelId': ch_id, 'channelTitle': ch_title,
                'latestTitle': '', 'latestVideoId': '', 'latestDate': '',
                'subscriberCount': subs, 'viewCount': 0, 'url': '',
                'error': str(e),
            })
    return results

def analyze_keywords(videos):
    """제목/설명에서 자주 등장하는 키워드 추출"""
    import re
    from collections import Counter
    stop = {'the','a','an','of','and','is','in','to','for','with','on','at','by','from',
            '영상','음악','플레이리스트','playlist','유튜브','채널','구독','좋아요','댓글','이'}
    words = []
    for v in videos:
        text = v['title'] + ' ' + v['description']
        tokens = re.findall(r'[가-힣a-zA-Z]{2,}', text.lower())
        words.extend([w for w in tokens if w not in stop and len(w) > 1])
    return Counter(words).most_common(20)

def send_kakao(token, text):
    """카카오 나에게 보내기"""
    data = urllib.parse.urlencode({
        'template_object': json.dumps({
            'object_type': 'text',
            'text': text[:1000],
            'link': {'web_url': 'https://studio.youtube.com', 'mobile_web_url': 'https://studio.youtube.com'}
        })
    }).encode('utf-8')
    req = urllib.request.Request(KAKAO_ME_URL, data=data,
                                 headers={'Authorization': f'Bearer {token}',
                                          'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

def build_report(videos, keywords, days=7):
    today = datetime.datetime.now().strftime('%Y.%m.%d')
    top10 = videos[:10]
    kw_str = ', '.join(f'{w}({c})' for w, c in keywords[:10])
    lines = [f'📊 유튜브 트렌드 리포트 ({today} 기준 최근 {days}일)',
             f'━━━━━━━━━━━━━━━━━━━━',
             f'🔑 핵심 키워드: {kw_str}',
             f'',
             f'🏆 조회수 TOP 10',
             ]
    for i, v in enumerate(top10, 1):
        vc = f"{v['viewCount']:,}"
        lines.append(f'{i}. {v["title"][:30]}')
        lines.append(f'   {v["channelTitle"]} | {vc}회 | {v["publishedAt"]}')
    lines += ['', '━━━━━━━━━━━━━━━━━━━━',
              f'총 {len(videos)}개 영상 분석 (한글 플레이리스트 채널, 구독자 5천+)']
    return '\n'.join(lines)

def run(params):
    action  = params.get('action', 'fetch_trends')
    api_key = params.get('apiKey', '')

    if action == 'fetch_trends':
        if not api_key:
            return {'error': 'YouTube API 키가 없습니다. 설정 > API 관리에서 등록해주세요'}
        try:
            videos = fetch_trends(
                api_key,
                query    = params.get('query', 'Playlist'),
                days     = int(params.get('days', 7)),
                min_subs = int(params.get('minSubs', 5000)),
            )
            keywords = analyze_keywords(videos)
            rivals = []
            try:
                rivals = fetch_rivals(api_key, days=30)
            except Exception as e:
                rivals = [{'name': '오류', 'error': str(e)}]
            return {
                'success': True,
                'videos': videos,
                'keywords': [{'word': w, 'count': c} for w, c in keywords],
                'rivals': rivals,
                'fetchedAt': datetime.datetime.now().isoformat(),
            }
        except Exception as e:
            return {'error': str(e)}

    elif action == 'send_kakao_report':
        kakao_token = params.get('kakaoToken', '')
        if not kakao_token:
            return {'error': '카카오 액세스 토큰이 없습니다'}
        if not api_key:
            return {'error': 'YouTube API 키가 없습니다'}
        try:
            videos   = fetch_trends(api_key, query=params.get('query', 'Playlist'),
                                    days=int(params.get('days', 7)),
                                    min_subs=int(params.get('minSubs', 5000)))
            keywords = analyze_keywords(videos)
            report   = build_report(videos, keywords, int(params.get('days', 7)))
            result   = send_kakao(kakao_token, report)
            if result.get('result_code') == 0:
                return {'success': True, 'message': '카카오톡 전송 완료'}
            return {'error': f'카카오 오류: {result}'}
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
