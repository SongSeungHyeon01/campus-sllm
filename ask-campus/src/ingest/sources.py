"""MVP 수집 대상: 학교 홈페이지 공개 페이지 일부 (FR-014).

공지 게시판(학사·일반·장학), 학사일정, 통학버스(영동·아산, 주말·방학 포함), 동아리현황.
첨부파일 본문 추출은 MVP 범위에서 뺐다 (게시글 본문만 수집).
"""
import hashlib
import re

from .fetch import BASE_URL, Fetcher
from .html_utils import clean, cms_content, table_records, text_lines
from .schema import Chunk, now_kst, pack

NOTICE_BOARDS = [
    # (게시판 경로, 카테고리, 메뉴 경로)
    ("/u1/community/academic.do", "학사정보", "홈 > 커뮤니티 > 공지사항 > 학사공지"),
    ("/u1/community/common.do", "일반공지", "홈 > 커뮤니티 > 공지사항 > 일반공지"),
    ("/u1/community/scholarship.do", "학사정보", "홈 > 커뮤니티 > 공지사항 > 장학공지"),
]
BUS_PAGES = [
    ("/u1/life/bus01.do", "영동", "영동캠퍼스 통학버스 (학기 중)", "홈 > 대학생활 > 통학버스 > 영동캠퍼스"),
    ("/u1/life/bus01-01.do", "영동", "영동캠퍼스 통학버스 (주말·공휴일·방학)", "홈 > 대학생활 > 통학버스 > 영동캠퍼스 > 주말,공휴일,방학"),
    ("/u1/life/bus02.do", "아산", "아산캠퍼스 통학버스 (학기 중)", "홈 > 대학생활 > 통학버스 > 아산캠퍼스"),
    ("/u1/life/bus02-01.do", "아산", "아산캠퍼스 통학버스 (주말·공휴일·방학)", "홈 > 대학생활 > 통학버스 > 아산캠퍼스 > 주말,공휴일,방학"),
]
CALENDAR = ("/u1/academic/academic-calendar.do", "홈 > 학사안내 > 학사일정")
CLUBS = ("/u1/life/status.do", "홈 > 대학생활 > 학생기구 > 동아리 > 동아리현황")

DATE = re.compile(r"(\d{2,4})\.(\d{1,2})\.(\d{1,2})")


def _id(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _iso(date_text: str) -> str | None:
    m = DATE.search(date_text or "")
    if not m:
        return None
    y, mo, d = m.groups()
    y = int(y) + 2000 if len(y) == 2 else int(y)
    return f"{y:04d}-{int(mo):02d}-{int(d):02d}"


def notices(f: Fetcher, pages: int = 2) -> list[Chunk]:
    """게시판 목록에서 최근 글을 골라 본문을 청크로 만든다."""
    out = []
    for path, category, menu in NOTICE_BOARDS:
        seen = set()
        for page in range(pages):
            listing = cms_content(f.get(f"{path}?mode=list&article.offset={page * 10}&articleLimit=10"))
            for a in listing.select("table tbody tr .b-title-box a[data-article-no]"):
                no = a["data-article-no"]
                if no in seen:          # 상단 고정 공지는 페이지마다 다시 나옴
                    continue
                seen.add(no)
                url = f"{BASE_URL}{path}?mode=view&articleNo={no}"
                view = cms_content(f.get(url))
                title = clean(view.select_one(".b-title-box").get_text(" "))
                body = view.select_one(".b-content-box")
                lines = text_lines(body) if body else []
                etc = view.select_one(".b-etc-box")
                posted = _iso(etc.get_text(" ") if etc else "")
                files = [clean(x.get_text(" ")) for x in view.select(".b-file-box a")]
                if files:
                    lines.append("첨부파일: " + ", ".join(files))
                header = f"[{menu.split(' > ')[-1]}] {title} (게시일 {posted or '미상'})"
                for i, text in enumerate(pack(header, lines or [title])):
                    out.append(Chunk(_id(url, i), category, title, text, url, now_kst(),
                                     {"campus": "공통", "posted_at": posted, "menu_path": menu}))
    return out


def calendar(f: Fetcher) -> list[Chunk]:
    """학사일정 목록 보기에서 일정을 하나씩 청크로 만든다."""
    path, menu = CALENDAR
    url = f"{BASE_URL}{path}?mode=list&article.offset=0&articleLimit=100"
    rows = cms_content(f.get(url)).select("table tbody tr")
    out = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        a = tds[1].select_one("a")
        title = clean(a.get_text(" ")) if a else clean(tds[1].get_text(" "))
        title = DATE.split(title)[0].strip() if DATE.search(title) else title
        period = clean(tds[2].get_text(" "))
        start = _iso(period)
        if not start:
            continue
        # 일정 하나를 청크 하나로: 월별로 묶으면 검색에서 다른 달 일정에 밀리는 문제가 있었음
        y, m = start[:4], int(start[5:7])
        text = f"[학사일정] {title}: {period} ({y}년 {m}월 일정)"
        out.append(Chunk(_id(url, title, period), "학사정보", f"학사일정: {title}", text,
                         f"{BASE_URL}{path}", now_kst(), {"campus": "공통", "posted_at": None, "menu_path": menu}))
    return out


def buses(f: Fetcher) -> list[Chunk]:
    """시간표 표를 '열 제목: 값' 문장으로 바꿔 청크로 만든다 (FR-015)."""
    out = []
    for path, campus, name, menu in BUS_PAGES:
        url = BASE_URL + path
        content = cms_content(f.get(url))
        notes = [ln for ln in text_lines(content) if "운행" in ln and len(ln) < 80][:3]
        for t_i, table in enumerate(content.find_all("table")):
            # 표 이름은 바로 위 제목(h3~h5)을 쓴다. caption은 표마다 같거나 틀린 경우가 있었음
            # (아산 주말 페이지의 '주말/공휴일'·'방학중' 두 표가 같은 caption, 영동 평일 표 caption은 '금요일만 운행…')
            heading = table.find_previous(["h3", "h4", "h5"])
            caption = table.find("caption")
            label = (clean(heading.get_text(" ")) if heading else
                     clean(caption.get_text(" ")) if caption else f"시간표 {t_i + 1}")
            lines = []
            for rec in table_records(table):
                cells = [f"{k}: {v}" for k, v in rec if v and v != k]
                if cells:
                    lines.append(" / ".join(cells))
            header = f"[{name}] {label}" + (f" ({notes[0]})" if notes else "")
            for i, text in enumerate(pack(header, lines)):
                out.append(Chunk(_id(url, t_i, i), "통학버스", name, text, url, now_kst(),
                                 {"campus": campus, "posted_at": None, "menu_path": menu}))
    return out


def clubs(f: Fetcher) -> list[Chunk]:
    path, menu = CLUBS
    url = BASE_URL + path
    lines = text_lines(cms_content(f.get(url)))
    return [Chunk(_id(url, i), "동아리·행사", "동아리현황", text, url, now_kst(),
                  {"campus": "공통", "posted_at": None, "menu_path": menu})
            for i, text in enumerate(pack("[동아리현황] 유원대학교 동아리 소개", lines))]


def collect_all(f: Fetcher, notice_pages: int = 2) -> list[Chunk]:
    chunks = []
    for name, fn in (("학사일정", calendar), ("통학버스", buses), ("동아리", clubs)):
        part = fn(f)
        print(f"  {name}: 청크 {len(part)}개")
        chunks += part
    part = notices(f, notice_pages)
    print(f"  공지: 청크 {len(part)}개")
    return chunks + part
