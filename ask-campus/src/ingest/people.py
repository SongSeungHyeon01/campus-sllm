"""수집 자료 전체를 보고 하는 개인정보 정리 (한 글만 봐서는 이름인지 알 수 없는 것).

11/22: 정해 둔 형태만 가려서 괄호 안 이름, 이름 나열, Q&A 글 속 학생 이름이 남아 있었다. 옛 글에는 초기 비밀번호 규칙도 있었다.
- 이름꼴: 흔한 성씨 + 두 글자. 자료 전체에서 자주 쓰이는 말(장학금, 편입학 등)은 일반 단어로 보고 가리지 않는다.
- 교수·교직원 소개 페이지에 나오는 이름은 학교가 안내하는 정보라 남긴다 (교수 안내 질문에 씀).
- 비밀번호가 무엇인지 알려 주는 문장은 지운다.
한계: 두 글자·네 글자 이름, 드문 성씨, 문장 속에 이름만 적힌 경우는 못 찾을 수 있다.
"""
import re
from collections import Counter

from .site_sources import _NAME

_STAFF_PAGE = re.compile(r"교수|조직도|직원|연락처|역대|총장")
_WORD = re.compile(rf"(?<![가-힣])({_NAME})(?![가-힣])")
_PAREN = re.compile(rf"(\(\s*)({_NAME}(?:\s*[,·]\s*{_NAME})*)(\s*\))")
_LIST = re.compile(rf"(?<![가-힣])({_NAME}(?:\s*[,·]\s*{_NAME}(?![가-힣])){{2,}})")
# '2차신청으로'처럼 숫자 뒤나 흔한 조사 앞의 말을 이름으로 보지 않는다 (이름을 바꾼다는 말 앞만)
_SAYS = re.compile(rf"(?<![가-힣\d])({_NAME})(?=\s?(?:입니다|이라고|라고 합니다|학생(?![가-힣])|님|에서\s*[가-힣○]{{3}}(?:으로|로)"
                   rf"|(?:으로|로)\s*(?:바꾸|바꿔|변경|개명|성을)))")
_ENG = re.compile(r"\b[A-Z]{2,}(?:\s[A-Z]{2,}){1,2}(?=\s*입니다)")
_PW = re.compile(r"(비밀번호|비번|패스워드|(?<![a-zA-Z])(?:pw|PW)(?![a-zA-Z])).{0,25}?(학번|주민|생년월일|뒷\s*(번호|자리)|동일|같습니다|초기\s*값)"
                 r"|(초기|기본)\s*(비밀번호|비번)")
# '비밀번호 :' 다음 줄에 값이 오거나(공지), 글에 서류 비밀번호 숫자를 적은 경우
_PW_VALUE = re.compile(r"(비밀번호|비번)\s*(?:[:：]\s*(?!\(안내)[^\n]+|(?:는|은)?\s*\d{2,}\S*)")
_SENT = re.compile(r"(?<=[다요]\.)(?=\s)|(?<=\n)")
COMMON = 8          # 자료 전체에서 이보다 자주 나오면 일반 단어로 본다
COMMON_POST = 4     # 학생 글에서


def scrub_corpus(rows: list[dict]) -> int:
    """rows의 content·title을 고치고 바뀐 조각 수를 돌려준다."""
    freq = Counter(w for r in rows for w in _WORD.findall(r["content"]))
    staff = {w for r in rows if _STAFF_PAGE.search(r["title"]) for w in _WORD.findall(r["content"])}

    def is_name(n: str, limit: int) -> bool:
        return n not in staff and freq[n] < limit

    def hide_list(text: str) -> str:
        return re.sub(_NAME, lambda m: "○○○" if is_name(m[0], COMMON) else m[0], text)

    changed = 0
    for r in rows:
        before = (r["content"], r["title"])
        post = r["category"] == "Q&A" or "reinstatement" in r["source_url"]
        c = _PAREN.sub(lambda m: m[1] + hide_list(m[2]) + m[3], r["content"])
        c = _LIST.sub(lambda m: hide_list(m[1]), c)
        if post:
            for n in {m[1] for m in _SAYS.finditer(c)}:
                if is_name(n, COMMON_POST):
                    c = c.replace(n, "○○○")
            c = _ENG.sub("○○○", c)
        c = _PW_VALUE.sub(lambda m: m[1] + ": (안내 생략)", c)
        if _PW.search(c):
            c = "".join("(비밀번호 안내 생략)\n" if _PW.search(s) else s for s in _SENT.split(c))
        r["content"] = c
        r["title"] = _PAREN.sub(lambda m: m[1] + hide_list(m[2]) + m[3], r["title"])
        changed += (r["content"], r["title"]) != before
    return changed
