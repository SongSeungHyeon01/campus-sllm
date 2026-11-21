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


# ── 공모전 모음 사이트 (11/21 사용자 요청: 'AI소프트웨어학과인데 해커톤 등 외부 공모전 전부 보는 방법') ──
# 이용약관을 읽고 자동 수집을 막는 조항이 없는 곳만 쓴다 (11/21 확인). 두 곳 모두 '상업적 이용'만 금지하므로
# 비상업 캡스톤에서 제목·주최·마감일·원문 링크만 보여 주고 본문은 가져오지 않는다. 6시간에 한 번만 읽는다.
# - 위비티 (wevity.com/?c=intro&s=4), 콘테스트코리아 (contestkorea.com/terms/service.php)
#   학과마다 맞는 공모전이 다르므로(간호·조리·영상 등) 공모전 분야 전체를 읽고, 학과 고르기는 rag.py가 한다.
#   이벤트·경품(위비티 gub=2)과 대외활동·봉사활동은 공모전이 아니라서 뺀다.
# 뺀 곳: 링커리어·요즘것들·씽굿·MLH (약관이 자동 수집이나 무단 복제를 금지), 데이콘·Devpost·캠퍼스픽·올콘·대티즌
# (약관을 확인하지 못함. 데이콘은 봇 확인 페이지(HTTP 202)를 돌려줘 우회하지 않음). Kaggle·K-Startup은 키가 필요한 공식 API라 키를 받으면 붙인다.
import threading
from concurrent.futures import ThreadPoolExecutor

_UA = {"User-Agent": "AskCampusBot/0.1 (U1 University capstone)"}
WEVITY = "https://www.wevity.com/"
_WEVITY_CATS = (1, 2, 3, 10, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 88)
CONTESTKOREA = "https://www.contestkorea.com/sub/"
_CK_CATS = ("030110001", "030210001", "030310001", "030610001", "030810001", "030910001",
            "031210001", "031410001", "031610001", "031810001")
_SITE_KEY = "contest_sites"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.read().decode("utf-8", "replace")


def _wevity(job: tuple[int, int], today: datetime) -> list[dict]:
    cidx, gp = job
    page = _get(f"{WEVITY}?c=find&s=1&gub=1&cidx={cidx}&gp={gp}")
    out = []
    for li in re.findall(r"<li[^>]*>\s*<!--class=\"bg\" -->(.*?)</li>", page, re.S):
        a = re.search(r'<a href="(\?[^"]+)">(.*?)</a>', li, re.S)
        day = re.search(r'<div class="day">\s*(D-(\d+)|D-day)?.*?class="dday (\w+)"', li, re.S)
        if not a or not day or day[3] not in ("ing", "soon"):
            continue
        days = int(day[2]) if day[2] else 0
        organ = re.search(r'<div class="organ">(.*?)</div>', li, re.S)
        field = re.search(r'<div class="sub-tit">분야\s*:\s*(.*?)</div>', li, re.S)
        out.append({"title": _clean(re.sub(r"<span.*?</span>", "", a[2], flags=re.S)),
                    "host": _clean(organ[1]) if organ else "",
                    "deadline": (today + timedelta(days=days)).strftime("%Y-%m-%d"),
                    "url": WEVITY + a[1].replace("&amp;", "&"), "site": "위비티",
                    "field": _clean(field[1]) if field else ""})
    return out


def _contestkorea(job: tuple[str, int], today: datetime) -> list[dict]:
    code, pg = job
    page = _get(f"{CONTESTKOREA}list.php?displayrow=12&int_gbn=1&Txt_bcode={code}&page={pg}")
    block = page.split('class="list_style_2"', 1)[-1].split('class="pagination"', 1)[0]
    out = []
    for li in block.split('<div class="title">')[1:]:            # 첫 항목만 class가 붙어 있어 제목 칸으로 나눈다
        a = re.search(r'<a href="(view\.php[^"]+)">.*?<span class="txt">(.*?)</span>', li, re.S)
        cond = re.search(r'class="condition">([^<]*)', li)
        rng = re.search(r"<em>접수</em>\s*(\d{2})\.(\d{2})~(\d{2})\.(\d{2})", li)
        if not a or not rng or not cond or cond[1].strip() not in ("접수중", "마감임박"):
            continue
        host = re.search(r"<strong>주최</strong>\s*\.\s*([^<]*)", li)
        field = re.search(r'<span class="category">([^<]*)', li)
        end = today.replace(month=int(rng[3]), day=int(rng[4]))
        if end.strftime("%m%d") < today.strftime("%m%d"):
            end = end.replace(year=today.year + 1)            # 12월에 '01.15' 마감 → 다음 해
        out.append({"title": _clean(a[2]), "host": _clean(host[1]) if host else "",
                    "deadline": end.strftime("%Y-%m-%d"), "url": CONTESTKOREA + a[1].replace("&amp;", "&"),
                    "site": "콘테스트코리아", "field": _clean(field[1]).replace("•", "/") if field else ""})
    return out


def site_contests(now: datetime) -> list[dict]:
    """두 사이트에서 접수 중인 공모전 (모든 분야). [{title, host, deadline, url, site}] 마감 빠른 순, 같은 공모전은 한 번."""
    hit = _cache.get(_SITE_KEY)
    if hit:
        items = hit[1]
        # 6시간이 지났으면 지금 질문은 가진 목록으로 답하고, 새로 읽기는 뒤에서 한다 (다 읽는 데 15초쯤 걸림)
        if time.time() - hit[0] >= CACHE_SEC and not _refreshing.locked():
            threading.Thread(target=_refresh_sites, args=(now,), daemon=True).start()
    else:
        items = _refresh_sites(now)
    return _dedupe(items, now)


_refreshing = threading.Lock()


def _refresh_sites(now: datetime) -> list[dict]:
    with _refreshing:
        hit = _cache.get(_SITE_KEY)                        # 기다리는 동안 다른 쪽(서버 시작 때)이 이미 읽었으면 그것을 쓴다
        if hit and time.time() - hit[0] < CACHE_SEC:
            return hit[1]
        today =now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        jobs = ([(_wevity, (c, gp)) for c in _WEVITY_CATS for gp in (1, 2)]       # 분야마다 앞 2쪽 (최근 등록 순)
                + [(_contestkorea, (c, pg)) for c in _CK_CATS for pg in (1, 2)])

        def run(job):
            try:
                return job[0](job[1], today)
            except Exception:
                return []                                     # 한 곳이 실패해도 나머지는 보여 준다
        with ThreadPoolExecutor(max_workers=3) as pool:      # 사이트에 부담을 주지 않게 3개씩
            items = [it for part in pool.map(run, jobs) for it in part]
        if items:
            _cache[_SITE_KEY] = (time.time(), items)
        return items or (_cache.get(_SITE_KEY) or (0, []))[1]


def _dedupe(items: list[dict], now: datetime) -> list[dict]:
    # 두 사이트에 같은 공모전이 이름만 조금 다르게 올라온다 ('2026 서울관광 프롬프톤' / '[2026 서울관광 프롬프톤] 참가자모집')
    out, seen = [], []
    for it in sorted(items, key=lambda x: x["deadline"]):
        key = re.sub(r"참가자?모집|모집|안내|공고|[^가-힣A-Za-z0-9]", "", it["title"]).lower()
        if it["deadline"] < now.strftime("%Y-%m-%d") or any(
                len(min(key, k, key=len)) >= 6 and (key in k or k in key) for k in seen):
            continue
        seen.append(key)
        out.append(it)
    return out
