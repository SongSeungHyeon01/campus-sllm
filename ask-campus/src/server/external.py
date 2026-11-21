"""외부 공모전 정보. 공모전 목록 질문에서만 쓴다. 둘 다 자동 조회를 공식으로 허용하는 API다.

1) 충청남도 공모전 일정 OPEN API (키 없음): 충남도 공모전과 접수 기간. 출처 표시 필요 (공공누리).
   https://www.chungnam.go.kr/cnbbs/openApiMainFxList.do
2) 네이버 검색 API (뉴스): 전국 공모전 소식.
   링커리어 등 민간 공모전 사이트는 약관이 자동화 프로그램 접속을 금지해서 쓰지 않는다 (11/20 확인).

네이버:
- 키는 ask-campus/.env의 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (git 제외). 없으면 조용히 건너뛴다.
- 학생 질문 문장은 보내지 않는다. '대학생 공모전'과 주제어(예: 'AI')만 검색어로 보낸다.
- 같은 검색어는 6시간 동안 저장해 두고 다시 쓴다 (무료 한도: 하루 2만 5천 건).
- 최근 60일 안의 기사 중 제목에 공모전·경진대회·공모가 들어간 것만 고른다.
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from . import config

API = "https://openapi.naver.com/v1/search/news.json"
CACHE_SEC = 6 * 3600
_cache: dict[str, tuple[float, list[dict]]] = {}
_TAG = re.compile(r"<[^>]+>")
_CONTEST = re.compile(r"공모전|경진대회|공모|콘테스트|해커톤")


def _keys() -> tuple[str, str]:
    """환경 변수가 있으면 그것을, 없으면 .env에서 네이버 키 두 개만 읽는다 (학교 계정 줄은 읽지 않음)."""
    import os
    cid, naver_sec = os.getenv("NAVER_CLIENT_ID", ""), os.getenv("NAVER_CLIENT_SECRET", "")
    env = config.ROOT / ".env"
    if (not cid or not naver_sec) and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "NAVER_CLIENT_ID" and not cid:
                cid = v.strip()
            elif k.strip() == "NAVER_CLIENT_SECRET" and not naver_sec:
                naver_sec = v.strip()
    return cid, naver_sec


def enabled() -> bool:
    cid, naver_sec = _keys()
    return bool(cid and naver_sec)


def _clean(text: str) -> str:
    return html.unescape(_TAG.sub("", text)).strip()


CHUNGNAM_API = "https://www.chungnam.go.kr/cnbbs/openApiMainFxList.do?numOfRows=100&pageNo=1"
CHUNGNAM_PAGE = "https://www.chungnam.go.kr"


def chungnam_contests(now: datetime, limit: int = 5) -> list[dict]:
    """충청남도 공모전 중 접수 마감이 지나지 않은 것. [{title, start, deadline, url}] 마감 빠른 순.

    응답: [{"items": [{"contestNm", "schedules": [{"schdulNm": "작품접수", "sdate": "2026-11-16 09:00", "edate": …}]}]}]
    """
    hit = _cache.get(CHUNGNAM_API)
    if hit and time.time() - hit[0] < CACHE_SEC:
        items = hit[1]
    else:
        req = urllib.request.Request(CHUNGNAM_API, headers={"User-Agent": "AskCampusBot/0.1 (U1 University capstone)"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.load(r)
            items = (data[0] if isinstance(data, list) else data).get("items", [])
        except Exception:
            return []
        _cache[CHUNGNAM_API] = (time.time(), items)
    today = now.strftime("%Y-%m-%d %H:%M")
    out = []
    for it in items:
        apply = [s for s in it.get("schedules") or [] if "접수" in (s.get("schdulNm") or "") and s.get("edate")]
        if not apply:
            continue
        s = apply[0]
        if s["edate"] >= today:
            out.append({"title": (it.get("contestNm") or "").strip(), "start": s.get("sdate", "")[:10],
                        "deadline": s["edate"][:10], "url": CHUNGNAM_PAGE})
    return sorted(out, key=lambda x: x["deadline"])[:limit]


def contest_news(topic_words: list[str], now: datetime, limit: int = 5) -> list[dict]:
    """[{title, url, date}] 최신순. 키가 없거나 호출이 실패하면 빈 목록."""
    cid, naver_sec = _keys()
    if not cid or not naver_sec:
        return []
    query = " ".join([*topic_words[:2], "대학생 공모전"])
    hit = _cache.get(query)
    if hit and time.time() - hit[0] < CACHE_SEC:
        items = hit[1]
    else:
        url = f"{API}?{urllib.parse.urlencode({'query': query, 'display': 30, 'sort': 'date'})}"
        req = urllib.request.Request(url, headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": naver_sec})  # privacy-allow: 네이버가 정한 헤더 이름. 값은 .env에서 읽음
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                items = json.load(r).get("items", [])
        except Exception:
            return []
        _cache[query] = (time.time(), items)
    since = now - timedelta(days=60)
    out, seen = [], set()
    for it in items:
        title = _clean(it.get("title", ""))
        if not _CONTEST.search(title) or title in seen:
            continue
        try:
            date = parsedate_to_datetime(it.get("pubDate", ""))
        except (TypeError, ValueError):
            continue
        if date.replace(tzinfo=None) < since.replace(tzinfo=None):
            continue
        seen.add(title)
        out.append({"title": title, "url": it.get("originallink") or it.get("link"), "date": date.strftime("%m.%d")})
        if len(out) >= limit:
            break
    return out
