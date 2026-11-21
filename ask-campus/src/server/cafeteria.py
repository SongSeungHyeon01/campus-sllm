"""학식(구내식당) 메뉴는 코드가 날짜로 골라 답한다 (sLLM을 쓰지 않음).

11/20: '학식 오늘 메뉴'를 물었더니(금요일) sLLM이 한 주 식단 중 화요일 메뉴를 골라 답했다.
식단은 날짜별로 나뉜 정해진 형식이라 통학버스 시간표처럼 코드가 오늘·내일·요일을 계산해서 고른다.

원문 형식 (사이트 수집 'cafeteria.do', 매주 월요일 다시 수집):
  2026.11.16 ~ 2026.11.22 / 11.16 / 월 / [아산 중식] / : 백미밥 / /돈육김치찌개 … / [영동 석식] … / 11.17 / 화 / …
"""
import re
from datetime import datetime, timedelta

from . import db

INTENT = ("학식", "식단", "구내식당", "중식", "석식", "급식")
MEAL_WORDS = ("메뉴", "점심", "저녁", "밥")
_WEEKDAYS = "월화수목금토일"
_RANGE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(\d{4})\.(\d{2})\.(\d{2})")
_DAY = re.compile(r"^(\d{2})\.(\d{2})$")
_SECTION = re.compile(r"^\[(아산|영동) (중식|석식)\]$")
_DAY_WORD = re.compile(r"([월화수목금토일])(?:요일|욜)")


def is_menu_question(question: str) -> bool:
    """학식 질문인가. '오늘 점심 뭐 나와?'처럼 '학식·메뉴'라는 말이 없어도 끼니 + '뭐 나와·뭐 먹·뭐야'면 학식으로 본다."""
    q = question.replace(" ", "")
    if any(w in q for w in INTENT):
        return True
    meal = any(w in q for w in ("점심", "저녁", "아침"))
    asks_food = any(w in q for w in ("메뉴", "뭐나와", "뭐나오", "뭐먹", "뭐야", "뭐임", "반찬", "식사"))
    return ("메뉴" in q and any(w in q for w in ("오늘", "내일", "요일"))) or (meal and asks_food)


def _load() -> tuple[tuple[str, str] | None, dict[str, dict[tuple[str, str], list[str]]]]:
    """(주간 시작·끝, {날짜: {(캠퍼스, 끼니): [메뉴…]}})"""
    with db.connect() as con:
        rows = con.execute("SELECT content FROM chunk WHERE source_url LIKE '%cafeteria%' ORDER BY rowid").fetchall()
    lines = []
    for r in rows:
        lines += [ln.strip() for ln in r["content"].split("\n")[1:] if ln.strip()]   # 첫 줄은 '[유원대] 학교 구내식당'
    text = "\n".join(lines)
    m = _RANGE.search(text)
    week = (f"{m[1]}-{m[2]}-{m[3]}", f"{m[4]}-{m[5]}-{m[6]}") if m else None
    year = m[1] if m else str(datetime.now().year)
    days: dict[str, dict] = {}
    day, sec = None, None
    for ln in lines:
        if d := _DAY.match(ln):
            day, sec = f"{year}-{d[1]}-{d[2]}", None
            days[day] = {}
        elif day and (s := _SECTION.match(ln)):
            sec = (s[1], s[2])
            days[day][sec] = []
        elif day and sec and not ln.startswith("상기") and ln not in _WEEKDAYS:
            # 한 줄이 한 음식이다 (': 백미밥', '/야채샐러드*드레싱/음료'). 줄 안의 '/'는 음식 이름의 일부라 자르지 않는다
            item = re.sub(r"^[:/]\s*", "", ln).strip()
            if item:
                days[day][sec].append(item)
    return week, days


def _target(question: str, now: datetime) -> tuple[list[datetime], str]:
    """물은 날짜들과 설명. 이번 주면 그 주 평일 전체."""
    q = question.replace(" ", "")
    shift = 7 if ("다음주" in q or "담주" in q) else -7 if "지난주" in q else 0
    monday = now - timedelta(days=now.weekday()) + timedelta(days=shift)
    if m := _DAY_WORD.search(q):
        return [monday + timedelta(days=_WEEKDAYS.index(m[1]))], f"{m[1]}요일"
    if shift or "이번주" in q or "일주일" in q or "한주" in q:
        return [monday + timedelta(days=i) for i in range(5)], "그 주"
    if "모레" in q:
        return [now + timedelta(days=2)], "모레"
    if "내일" in q:
        return [now + timedelta(days=1)], "내일"
    if "어제" in q:
        return [now - timedelta(days=1)], "어제"
    return [now], "오늘"


def answer(question: str, campus: str | None, now: datetime) -> tuple[str, bool] | None:
    """학식 질문이면 (답 문장, 그날 식단을 찾았나). 식단 자료가 아예 없으면 None (일반 검색으로)."""
    week, days = _load()
    if not days:
        return None
    dates, label = _target(question, now)
    q = question.replace(" ", "")
    meals = ["중식"] if ("점심" in q or "중식" in q) else ["석식"] if ("저녁" in q or "석식" in q) else ["중식", "석식"]
    campuses = [campus] if campus in ("아산", "영동") else ["아산", "영동"]
    out, found = [], False
    for d in dates:
        key = d.strftime("%Y-%m-%d")
        head = f"{d.month}월 {d.day}일({_WEEKDAYS[d.weekday()]})"
        if key not in days:
            if week and week[0] <= key <= week[1]:
                out.append(f"{head}에는 구내식당 식단이 없습니다.")
            elif week:
                span = f"{week[0][5:].replace('-', '.')}~{week[1][5:].replace('-', '.')}"
                out.append(f"{head} 식단은 아직 올라오지 않았습니다. 지금 있는 식단은 {span} 주간입니다." if key > week[1]
                           else f"{head} 식단은 남아 있지 않습니다. 지금 있는 식단은 {span} 주간입니다.")
            continue
        for c in campuses:
            for meal in meals:
                items = days[key].get((c, meal))
                if items:
                    found = True
                    out.append(f"{head} {c} {meal}: {', '.join(items)}")
    if not out:
        return None
    tail = "\n\n식단은 시장 수급 상황에 따라 달라질 수 있습니다." if found else ""
    return "\n".join(out) + tail, found
