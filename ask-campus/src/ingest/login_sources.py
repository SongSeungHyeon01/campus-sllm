"""로그인해야 보이는 페이지를 수집한다: 커뮤니티 > FAQ, 커뮤니티 > Q&A (답변 달린 글만).

계정은 ask-campus/.env의 U1_ID, U1_PW에서 읽는다 (git에 올리지 않음). 계정 값은 출력하지 않는다.
개인정보 처리:
- Q&A 작성자 이름은 저장하지 않는다. 본문과 답변에 그 이름이 나오면 가린다.
- 전화번호, 학번, 이메일 형태도 가린다.
- 원본 HTML은 디스크에 남기지 않는다 (raw_dir 없음).
"""
import re
from pathlib import Path

from .fetch import BASE_URL, Fetcher
from .html_utils import clean, cms_content
from .schema import Chunk, now_kst, pack
from .sources import _id, _iso

ENV = Path(__file__).resolve().parents[2] / ".env"
FAQ = ("/u1/community/faq.do", "홈 > 커뮤니티 > FAQ")
QNA = ("/u1/community/qna.do", "홈 > 커뮤니티 > Q&A")

_PHONE = re.compile(r"0\d{1,2}[-\s.)]?\d{3,4}[-\s.]?\d{4}")
_STUDENT_NO = re.compile(r"(?<!\d)\d{8,10}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


class LoginError(RuntimeError):
    pass


def _account() -> tuple[str, str]:
    if not ENV.exists():
        raise LoginError(f"{ENV} 파일이 없습니다 (.env.example 참고)")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    uid, pw = env.get("U1_ID", ""), env.get("U1_PW", "")
    if not uid or not pw:
        raise LoginError(".env에 U1_ID, U1_PW를 채워 주세요")
    return uid, pw


def login(f: Fetcher) -> None:
    uid, pw = _account()
    f.get("/u1/login.do?auty=LOGIN")
    r = f.session.post(BASE_URL + "/custom/login/idLoginProc.do", timeout=f.timeout, allow_redirects=False,
                       data={"referer": FAQ[0], "site_id": "u1", "member_id": uid, "member_pw": pw})
    # 성공하면 referer로 보내고, 실패하면 로그인 페이지로 돌려보낸다
    if r.status_code not in (302, 303) or "login" in (r.headers.get("Location") or ""):
        raise LoginError("로그인 실패 (아이디·비밀번호 확인)")
    check = f.session.get(BASE_URL + FAQ[0], timeout=f.timeout, allow_redirects=False)
    if check.status_code != 200:
        raise LoginError("로그인 후에도 FAQ가 열리지 않습니다")


def mask(text: str, names: tuple[str, ...] = ()) -> str:
    for n in names:
        if n and len(n) >= 2:
            text = text.replace(n, "○○○")
    return _STUDENT_NO.sub("***", _PHONE.sub("***", _EMAIL.sub("***", text)))


# 학교 답변 대부분이 질문 원문을 "---- 원 본 글 시 작 ---- … ---- 원 본 글 종 료 ----"로 다시 붙인다
_QUOTE = re.compile(r"-{3,}\s*원\s*본\s*글\s*시\s*작\s*-{3,}.*?-{3,}\s*원\s*본\s*글\s*종\s*료\s*-{3,}", re.S)


def strip_quote(answer: str) -> str:
    return _QUOTE.sub("", answer).strip()


def _text(node) -> str:
    return clean(node.get_text("\n")) if node else ""


def faq(f: Fetcher) -> list[Chunk]:
    path, menu = FAQ
    out, offset = [], 0
    while True:
        page = cms_content(f.get(f"{path}?mode=list&articleLimit=10&article.offset={offset}"))
        items = page.select(".bn-list-faq01 li")
        for li in items:
            q = _text(li.select_one(".b-quest-box .b-title-box"))
            a = _text(li.select_one(".b-ans-box .b-ans"))
            if not q or not a:
                continue
            text = f"[학교 FAQ] Q. {q}\nA. {mask(a)}"
            out.append(Chunk(_id(path, q), "FAQ", f"FAQ: {q}", text, BASE_URL + path, now_kst(),
                             {"campus": "공통", "posted_at": None, "menu_path": menu}))
        if len(items) < 10:
            return out
        offset += 10


def qna(f: Fetcher, pages: int | None = None, since: str = "2021-01-01") -> tuple[list[Chunk], dict]:
    """Q&A 목록을 넘기며 답변이 달린 글만 청크로 만든다. since보다 오래된 글은 건너뛴다 (예전 규정이 섞이지 않게)."""
    path, menu = QNA
    out, stat = [], {"글": 0, "답변있음": 0, "오래됨": 0}
    page_no = 0
    while pages is None or page_no < pages:
        listing = cms_content(f.get(f"{path}?mode=list&articleLimit=10&article.offset={page_no * 10}"))
        rows = listing.select("table tbody tr")
        if not rows:
            break
        stop = False
        for tr in rows:
            a = tr.select_one(".b-title-box a[href*=articleNo]") or tr.select_one("a[href*=articleNo]")
            if not a:
                continue
            no = re.search(r"articleNo=(\d+)", a["href"]).group(1)
            writer = _text(tr.select_one(".b-writer"))
            posted = _iso(_text(tr.select_one(".b-date")))
            if posted and posted < since:
                stat["오래됨"] += 1
                stop = True             # 목록은 최신순이라 이후 글도 모두 오래됨
                break
            stat["글"] += 1
            url = f"{BASE_URL}{path}?mode=view&articleNo={no}"
            view = cms_content(f.get(url))
            titles = view.select(".b-title-box")
            bodies = view.select(".b-content-box")
            if len(bodies) < 2:         # 답변 없는 글
                continue
            stat["답변있음"] += 1
            names = tuple(n for n in writer.split() if re.fullmatch(r"[가-힣]{2,4}", n))
            q_title = mask(_text(titles[0]), names)
            q_body = mask(_text(bodies[0]), names)
            answer = mask(strip_quote("\n".join(_text(b) for b in bodies[1:])), names)
            if not answer:
                continue
            header = f"[학생 Q&A] {q_title} (게시일 {posted or '미상'})"
            lines = [f"질문: {q_body}", f"학교 답변: {answer}"]
            for i, text in enumerate(pack(header, lines)):
                out.append(Chunk(_id(url, i), "Q&A", f"Q&A: {q_title}", text, url, now_kst(),
                                 {"campus": "공통", "posted_at": posted, "menu_path": menu}))
        if stop:
            break
        page_no += 1
    return out, stat
