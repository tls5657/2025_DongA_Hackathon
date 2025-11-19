# streamlit_app/utils/youtube_api.py
import os
import math
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()  # .env 읽기

API_KEY = os.getenv("YOUTUBE_API_KEY")


def _compute_score(snippet: dict, stats: dict, query: str) -> float:
    """
    조회수, 좋아요 비율, 댓글 수, 제목/설명 키워드 매칭을 묶어서 점수로 계산.
    (최신성은 제외)
    """
    # 숫자 값들 안전하게 파싱
    view_count = int(stats.get("viewCount", 0))
    like_count = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))

    # 1) 조회수: 너무 큰 값이 튀지 않게 로그 스케일
    s_views = math.log10(view_count + 1)

    # 2) 좋아요 비율: like / view (0~1 사이) → 단순 스케일링
    like_ratio = like_count / view_count if view_count > 0 else 0.0
    s_like_ratio = like_ratio * 10  # 가중치용 스케일

    # 3) 댓글 수: 커뮤니티 반응, 역시 로그 스케일
    s_comments = math.log10(comment_count + 1)

    # 4) 제목/설명에 쿼리 문자열 포함 여부
    title = (snippet.get("title") or "").lower()
    description = (snippet.get("description") or "").lower()
    q = (query or "").lower()

    s_keyword = 0.0
    if q:
        if q in title:
            s_keyword += 1.0  # 제목에 포함되면 가중치 크게
        if q in description:
            s_keyword += 1.0  # 설명에 포함되면 약간 가중치

    # 최종 점수 (가중치는 필요에 따라 튜닝 가능)
    score = (
        1.0 * s_views +
        1.0 * s_like_ratio +
        0.5 * s_comments +
        1.0 * s_keyword
    )
    return score


def search_youtube_videos(query: str, max_results: int = 10):
    """키워드로 유튜브 영상 검색 후 '커스텀 점수' 순으로 정렬해서 리턴.

    반환 형식: [
        {
            "video_id": "...",
            "title": "...",
            "channel_title": "...",
            "thumbnail": "...",
            "view_count": 12345,
            "like_count": 123,
            "comment_count": 45,
            "published_at": "...",
            "score": 12.34,              # 커스텀 점수 (정렬 기준)
        },
        ...
    ]
    """
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY가 .env에 설정되어 있지 않습니다.")

    youtube = build("youtube", "v3", developerKey=API_KEY)

    # 1) 검색으로 videoId 리스트 가져오기
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results,
        order="relevance",  # 1차 필터는 유튜브 기본 관련도
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
    if not video_ids:
        return []

    # 2) statistics 호출해서 조회수/좋아요/댓글 가져오기
    videos_response = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids),
    ).execute()

    results = []
    for item in videos_response.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        score = _compute_score(snippet, stats, query)

        results.append(
            {
                "video_id": item.get("id"),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "thumbnail": snippet.get("thumbnails", {})
                .get("default", {})
                .get("url"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "published_at": snippet.get("publishedAt"),
                "score": score,
            }
        )

    # 커스텀 점수 내림차순 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
