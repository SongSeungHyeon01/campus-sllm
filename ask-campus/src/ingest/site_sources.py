"""학교 사이트 전체 수집: 메인 사이트(/u1) 메뉴 페이지 + 학과·대학원 사이트.

- 메뉴 페이지는 두 종류로 나눈다.
  - 게시판(목록에 articleNo 링크가 있음): since 이후 글만 본문까지 읽는다.
  - 일반 페이지: 본문 글을 그대로 청크로 만든다.
- 다른 수집기(sources.py, login_sources.py)가 이미 넣는 페이지는 건너뛴다.
- 학생이 쓰는 게시판(자유게시판·Q&A 류)은 전화번호·학번·이메일을 가린다. 학교가 올린 안내 페이지의 부서 전화번호는 그대로 둔다.
- 로그인한 세션을 받으면 www.u1.ac.kr의 로그인 전용 게시판도 읽는다.
"""
import re
from urllib.parse import urljoin, urlparse

from .fetch import BASE_URL, Fetcher
from .html_utils import clean, cms_content, page_title, soup_of, text_lines
from .login_sources import mask
from .schema import Chunk, now_kst, pack
from .sources import _id, _iso

# (이름, 시작 주소, 캠퍼스)
DEPARTMENTS = [
    ("사회복지학부", "https://www.u1.ac.kr/social/index.do", "영동"),
    ("산업안전보건학과", "https://www.u1.ac.kr/safety/index.do", "영동"),
    ("스마트평생교육학부", "https://www.u1.ac.kr/slife/index.do", "영동"),
    ("스마트팜학과", "https://www.u1.ac.kr/smartfarm/index.do", "영동"),
    ("자율설계학부", "https://www.u1.ac.kr/autonomy/index.do", "영동"),
    ("한국어문화학과", "https://www.u1.ac.kr/korean/index.do", "영동"),
    ("호텔조리베이커리학과", "https://ipsi.u1.ac.kr/bakery/index.do", "영동"),
    ("와인사이언스학과", "https://www.u1.ac.kr/wine/index.do", "영동"),
    ("치위생학과", "https://www.u1.ac.kr/dental/index.do", "영동"),
    ("물리치료학과", "https://www.u1.ac.kr/physical/index.do", "영동"),
    ("응급구조학과", "https://www.u1.ac.kr/emt119/index.do", "영동"),
    ("간호학과", "https://www.u1.ac.kr/nursing/index.do", "영동"),
    ("스포츠학부", "https://www.u1.ac.kr/sports/index.do", "영동"),
    ("미디어콘텐츠학과", "https://amc.u1.ac.kr/amc/index.do", "아산"),
    ("미래자동차학과", "https://www.u1.ac.kr/autocar/index.do", "아산"),
    ("AI소프트웨어학과", "https://www.u1.ac.kr/computer/index.do", "아산"),
    ("드론로봇응용학과", "https://www.u1.ac.kr/dr/index.do", "아산"),
    ("뷰티케어학과", "https://www.u1.ac.kr/beautycare/index.do", "아산"),
    ("작업치료학과", "https://www.u1.ac.kr/occup/index.do", "아산"),
    ("경찰소방행정학부", "https://www.u1.ac.kr/police/index.do", "아산"),
    ("문화복지융합학부", "https://www.u1.ac.kr/cultural/index.do", "아산"),
    ("국방인재개발학과", "https://www.u1.ac.kr/army/index.do", "아산"),
    ("초등특수교육과", "https://www.u1.ac.kr/elem/index.do", "아산"),
    ("중등특수교육과", "https://www.u1.ac.kr/sse/index.do", "아산"),
    ("유아교육과", "https://www.u1.ac.kr/ece2/index.do", "아산"),
    ("미래라이프융합학부", "https://www.u1.ac.kr/flife/index.do", "아산"),
    ("창의설계학부", "https://www.u1.ac.kr/creative/index.do", "아산"),
    ("글로벌K-컬처학과", "https://www.u1.ac.kr/k-culture/index.do", "아산"),
    ("파크골프지도학과", "https://www.u1.ac.kr/parkgolf/index.do", "아산"),
    ("교양융합학부", "https://www.u1.ac.kr/humanities/index.do", "공통"),
    ("대학원", "https://graduate.u1.ac.kr/graduate/index.do", "공통"),
]

# 다른 수집기가 이미 넣는 페이지
COVERED = ("/u1/academic/academic-calendar.do", "/u1/life/bus01.do", "/u1/life/bus01-01.do", "/u1/life/bus02.do",
           "/u1/life/bus02-01.do", "/u1/life/status.do", "/u1/community/academic.do", "/u1/community/common.do",
           "/u1/community/scholarship.do", "/u1/community/faq.do", "/u1/community/qna.do")
# 글이 거의 없는 페이지 (사진·영상·로고·교가·시험 페이지 등)
SKIP = re.compile(r"(gallery|photo|movie|video|promotional-video|logo|color|signature|symbol|song|test\d|sitemap|"
                  r"privacy|email\.do|policy\.do|academic-calendar-past|bidding)", re.I)
# 학생이 글을 쓰는 게시판: 개인정보 가림
STUDENT_BOARDS = re.compile(r"(free|qna|q-a|board|communication|compliment|report|counsel)", re.I)
MAIN_CATEGORY = {"academic": "학사정보", "life": "대학생활", "community": "공지", "administration": "대학행정",
                 "introduction": "대학소개", "guide": "안내"}
ARTICLE = re.compile(r"articleNo=(\d+)")


def _page_kind(content) -> str:
    """본문에 글 번호(articleNo) 링크가 있으면 게시판, 없으면 일반 안내 페이지로 본다."""
    return "board" if content.select("a[href*='articleNo']") else "page"


def _menu_links(f: Fetcher, start: str, prefix: str) -> list[str]:
    """시작 페이지의 메뉴에서 같은 사이트(prefix) 안의 페이지 주소를 모은다."""
    html = f.get(start)
    out = []
    for a in soup_of(html).select("a[href]"):
        url = urljoin(start, a["href"]).split("#")[0]
        path = urlparse(url).path
        if (urlparse(url).netloc == urlparse(start).netloc and path.startswith(prefix) and path.endswith(".do")
                and "mode=" not in url and not path.endswith(("/index.do", "/main.do"))):
            out.append(url.split("?")[0])
    return list(dict.fromkeys(out))


def _static(url: str, html: str, title_prefix: str, category: str, campus: str, menu: str) -> list[Chunk]:
    """일반 안내 페이지 본문을 청크로 만든다. 제목은 브라우저 탭 제목('졸업 | 유원대학교' → '졸업')을 쓴다."""
    content = cms_content(html)
    lines = text_lines(content)
    if sum(len(x) for x in lines) < 40:          # 거의 빈 페이지
        return []
    name = page_title(html) or menu.split(" > ")[-1]
    header = f"[{title_prefix}] {name}"
    return [Chunk(_id(url, i), category, f"{title_prefix}: {name}", text, url, now_kst(),
                  {"campus": campus, "posted_at": None, "menu_path": menu})
            for i, text in enumerate(pack(header, lines))]


def _board(f: Fetcher, url: str, first_html: str, title_prefix: str, category: str, campus: str, menu: str,
           since: str, max_pages: int) -> list[Chunk]:
    """게시판 목록을 쪽마다 넘기며 since 이후 글의 본문(답변 포함)과 첨부파일 이름을 청크로 만든다.

    한 쪽 안에 새 글이 하나도 없고 오래된 글만 있으면 멈춘다 (목록은 최신순).
    학생이 쓰는 게시판이면 전화번호·학번·이메일을 가린다.
    """
    out, seen = [], set()
    private = bool(STUDENT_BOARDS.search(urlparse(url).path))
    html = first_html
    for page in range(max_pages):
        if page:
            html = f.get(f"{url}?mode=list&articleLimit=10&article.offset={page * 10}")
        listing = cms_content(html)
        rows = listing.select("table tbody tr") or listing.select("li")
        new, old = 0, 0
        for row in rows:
            a = row.select_one("a[href*='articleNo']")
            if not a:
                continue
            no = ARTICLE.search(a["href"]).group(1)
            if no in seen:
                continue
            seen.add(no)
            posted = _iso(clean(row.get_text(" ")))
            if posted and posted < since:
                old += 1
                continue
            new += 1
            view_url = f"{url}?mode=view&articleNo={no}"
            try:
                view = cms_content(f.get(view_url))
            except Exception:                    # 비밀글·삭제된 글
                continue
            titles = [clean(t.get_text(" ")) for t in view.select(".b-title-box")]
            bodies = view.select(".b-content-box")
            title = titles[0] if titles else clean(a.get_text(" "))
            lines = [ln for b in bodies for ln in text_lines(b)] or [title]
            files = [clean(x.get_text(" ")) for x in view.select(".b-file-box a")]
            if files:
                lines.append("첨부파일: " + ", ".join(files))
            if private:
                lines, title = [mask(x) for x in lines], mask(title)
            header = f"[{title_prefix}] {title} (게시일 {posted or '미상'})"
            for i, text in enumerate(pack(header, lines)):
                out.append(Chunk(_id(view_url, i), category, f"{title_prefix}: {title}", text, view_url, now_kst(),
                                 {"campus": campus, "posted_at": posted, "menu_path": menu}))
        if new == 0 and (old or not rows):           # 이 쪽부터는 오래된 글뿐
            break
    return out


def _crawl(f: Fetcher, url: str, title_prefix: str, category: str, campus: str, menu: str,
           since: str, max_pages: int) -> list[Chunk]:
    """페이지 하나를 읽어 게시판이면 _board, 아니면 _static으로 넘긴다. 실패한 페이지는 건너뛰고 수집을 이어간다."""
    try:
        html = f.get(url)
    except Exception as e:                       # 없는 페이지·권한 없음은 건너뜀
        print(f"    건너뜀 {url}: {type(e).__name__}")
        return []
    if "member_pw" in html:
        print(f"    로그인 필요 {url}")
        return []
    try:
        if _page_kind(cms_content(html)) == "board":
            return _board(f, url, html, title_prefix, category, campus, menu, since, max_pages)
        return _static(url, html, title_prefix, category, campus, menu)
    except Exception as e:                       # 본문 영역이 없는 페이지(외부 연결·팝업 등)나 글 하나의 오류
        print(f"    건너뜀 {url}: {type(e).__name__}")
        return []


def main_site(f: Fetcher, since: str, max_pages: int) -> list[Chunk]:
    """메인 사이트 첫 화면의 전체 메뉴(/u1/...)를 수집한다. 분류는 주소 두 번째 칸(academic, life …)으로 정한다."""
    out = []
    links = [u for u in _menu_links(f, BASE_URL + "/u1/main.do", "/u1/")
             if urlparse(u).path not in COVERED and not SKIP.search(u)]
    print(f"  메인 사이트 메뉴 {len(links)}개")
    for url in links:
        seg = urlparse(url).path.split("/")[2]
        category = MAIN_CATEGORY.get(seg, "학교안내")
        part = _crawl(f, url, "유원대", category, "공통", f"홈 > {seg} > {urlparse(url).path}", since, max_pages)
        out += part
    return out


def departments(f: Fetcher, since: str, max_pages: int) -> list[Chunk]:
    """DEPARTMENTS의 학과·대학원 사이트마다 첫 화면 메뉴를 따라 수집한다. 캠퍼스는 학과 소속 캠퍼스로 붙인다."""
    out = []
    for name, start, campus in DEPARTMENTS:
        prefix = "/" + urlparse(start).path.split("/")[1] + "/"
        try:
            links = [u for u in _menu_links(f, start, prefix) if not SKIP.search(u)]
        except Exception as e:
            print(f"  {name}: 시작 페이지 실패 {type(e).__name__}")
            continue
        n = len(out)
        for url in links:
            out += _crawl(f, url, name, "학과", campus, f"대학·대학원 > {name} > {urlparse(url).path}", since, max_pages)
        print(f"  {name}: 페이지 {len(links)}개, 청크 {len(out) - n}개")
    return out
