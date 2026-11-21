"""모든 답변의 가독성 정리 (11/21 사용자 요청: '답변이 길어지게 될 때 가독성을 높이게 모든 답변에 적용').

sLLM 답, 공지 원문 일부, FAQ, 코드가 만든 답(버스·학식·공모전)이 모두 여기를 지나간다. 내용은 바꾸지 않고 줄만 나눈다.
- 목록 기호(-, *, •, ○, ▶, □ …)는 '· '로 통일한다. 화면(chat.html)은 '· ' 줄을 들여쓰기해 보여 준다.
- 공지 원문처럼 '가. 대회명: … 나. 주 제: …'가 한 줄에 붙어 있으면 항목마다 줄을 나눈다.
- 문장이 세 개 이상 붙은 긴 문단은 첫 문장(핵심)을 따로 두고 나머지를 한 문장씩 줄을 나눈다.
- 빈 줄은 최대 한 줄.
짧은 답(한두 문장)은 그대로 둔다.
"""
import re

_BULLET = re.compile(r"^\s*(?:[-*•●◎▪○◦▶▷►□■◆◇ㅇ]|•)\s+")
_BULLET_ONLY = re.compile(r"^\s*[-*•●◎▪○◦▶▷►□■◆◇]\s*$")
# FAQ '1. 해당 학과에 사전 연락 2. 방학시작부터 …'. 뒤에 한글이 올 때만 ('2026. 6. 8.' 같은 날짜는 그대로)
_INLINE_DOT = re.compile(r"\s+(?=(?:[1-9]|1[0-9])\.\s[가-힣])")
# 한 줄 안에 붙은 '가. … 나. … 다. …' / '1) … 2) …' / '① … ② …'
_INLINE_KO = re.compile(r"\s+(?=[가나다라마바사아자차카타파하]\.\s)")
_INLINE_NUM = re.compile(r"\s+(?=(?:[1-9]|1[0-9])\)\s)")
_INLINE_CIRCLED = re.compile(r"\s+(?=[①-⑳])")
_INLINE_NOTE = re.compile(r"\s+(?=※)")
# 문장 끝: '…다.' '…요.' 뒤의 공백. '2026.6.8.' 같은 날짜나 '08:00'은 자르지 않는다
_SENT = re.compile(r"(?<=[다요]\.)\s+(?=\S)")
LONG = 80           # 이보다 긴 문단만 문장 단위로 나눈다


def _split_inline(line: str) -> list[str]:
    if len(line) < 60:
        return [line]
    for pat in (_INLINE_KO, _INLINE_NUM, _INLINE_DOT, _INLINE_CIRCLED):
        parts = pat.split(line)
        if len(parts) >= 3:                       # 항목이 셋 이상 붙어 있을 때만 (우연한 '다. '에 걸리지 않게)
            line = "\n".join(p.strip() for p in parts)
            break
    return [p for p in _INLINE_NOTE.split(line.replace("\n", "\u0000")) for p in p.split("\u0000")]


def _split_sentences(line: str) -> list[str]:
    if len(line) < LONG or line.startswith("· "):
        return [line]
    sents = _SENT.split(line)
    return sents if len(sents) >= 3 else [line]


def tidy(text: str) -> str:
    if not text:
        return text
    out = []
    raw_lines = text.replace("\r\n", "\n").split("\n")
    # 기호만 있는 줄('●')은 다음 줄과 붙인다 (공지 원문에서 기호와 내용이 줄이 나뉘어 들어옴)
    merged = []
    for ln in raw_lines:
        if merged and _BULLET_ONLY.match(merged[-1]):
            merged[-1] = merged[-1].strip() + " " + ln.strip()
        else:
            merged.append(ln)
    for raw in merged:
        line = raw.rstrip()
        if not line.strip():
            out.append("")
            continue
        line = _BULLET.sub("· ", line) if not line.lstrip().startswith("※") else line.strip()
        for part in _split_inline(line.strip()):
            out.extend(_split_sentences(part.strip()))
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
