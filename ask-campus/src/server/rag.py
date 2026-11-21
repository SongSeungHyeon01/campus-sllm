"""질문 하나를 처리한다 (API 명세 1-2 서버 처리 순서).

1) FAQ(관리자가 등록한 답변)에서 거의 같은 질문을 찾으면 그 답변을 그대로 돌려줌
2) 아니면 청크를 검색해 기준 이상이면 sLLM이 근거만으로 답변
3) 근거가 없거나 sLLM이 "찾을 수 없습니다"라고 하면 답변 대기에 자동 등록 (FR-005, FR-028)

청크는 Chroma에서, FAQ·답변 대기는 SQLite vec 열에서 찾는다 (db.py 설명 참고).
"""
import json
import re
import time
from datetime import datetime, timedelta

import numpy as np

from . import cafeteria, clarifier, config, db, departments, external, index, llm, readable

SOURCE_GAP = 0.04          # 출처로 보여 줄 근거의 점수 차이 한도

# 11/21 사용자 결정: 조교에게 넘기는 흐름을 없앴다. 못 찾은 질문은 관리 웹 '답변 대기'에 쌓이고 관리자가 답을 등록한다
NOT_FOUND_ANSWER = "해당 정보를 찾을 수 없습니다. 학교 홈페이지나 담당 부서에 문의해 주세요."


def _blob(vec: list[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _nearest(con, sql: str, qvec: list[float]):
    """sql이 돌려준 행 중 vec이 질문과 가장 비슷한 행과 점수. 임베딩은 정규화돼 있어 내적 = 코사인."""
    rows = [r for r in con.execute(sql).fetchall() if r["vec"]]
    if not rows:
        return None, 0.0
    mat = np.stack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])
    scores = mat @ np.asarray(qvec, dtype=np.float32)
    i = int(scores.argmax())
    return rows[i], float(scores[i])


def _campus_filter(campus: str | None) -> dict | None:
    return {"campus": {"$in": [campus, "공통"]}} if campus in ("영동", "아산") else None


def _sources_from_chunks(hits: list[dict]) -> list[dict]:
    """출처는 가장 비슷한 근거와 점수 차이가 작은 것만 보여 준다.
    (예: '등록금 환불 2/3선' 질문에 1/2선·5/6선 일정까지 출처로 나오던 문제)"""
    best = hits[0]["score"] if hits else 0
    hits = [h for h in hits if h["score"] >= best - SOURCE_GAP]
    seen, out = set(), []
    for h in hits:
        m = h["meta"]
        key = (m.get("title"), m.get("source_url"))
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": m.get("title"), "kind": "공지", "source_url": m.get("source_url"),
                    "menu_path": m.get("menu_path"), "collected_at": m.get("collected_at")})
    return out[:config.CONTEXT_K]


_WEEKDAYS = "월화수목금토일"


def _now() -> datetime:
    """현재 시각 (KST). 시험에서는 이 함수를 바꿔 시각을 정한다 (scripts/time_test.py)."""
    return datetime.now(db.KST)


def _now_text(now: datetime) -> str:
    """sLLM에 넘기는 현재 시각 (FR-003: 서버의 현재 날짜·시각을 함께 전달). 예: 2026년 10월 12일 (월요일) 07:37"""
    return f"{now:%Y년 %m월 %d일} ({_WEEKDAYS[now.weekday()]}요일) {now:%H:%M}"


def _day_type(question: str, now: datetime) -> tuple[str, bool]:
    """어느 시간표를 볼지: '평일' / '주말' / '방학'. 질문에 적힌 말을 먼저 보고, 없으면 오늘 요일로 정한다.
    두 번째 값은 질문에 날짜 종류가 직접 적혀 있었는지 (오늘이 아닌 날을 물으면 '다음 차' 계산을 하지 않음)."""
    if "방학" in question:
        return "방학", True
    if any(w in question for w in ("주말", "토요일", "일요일", "공휴일", "휴일")):
        return "주말", True
    if any(w in question for w in ("평일", "월요일", "화요일", "수요일", "목요일", "금요일", "학기 중")):
        return "평일", True
    # 11/21 사용자 요청: 학사일정의 방학 기간(예: '2026학년도 동계방학: 2026.12.16 ~ 2027.02.28')이면 방학 표,
    # 아니면 학기 중(월~금) 표. 토요일에 '(주말·공휴일·방학)' 페이지 표로 답해 방학 시간표처럼 보였다.
    # 학기 중 주말이면 주말/공휴일 표 (같은 사용자 지적: 주말 시간표가 따로 있는데 평일 표를 보여 주면 안 됨)
    if _in_vacation(now):
        return "방학", False
    return ("주말" if now.weekday() >= 5 else "평일"), False


_VACATION = re.compile(r"방학:\s*(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(\d{4})\.(\d{2})\.(\d{2})")


def _in_vacation(now: datetime) -> bool:
    """수집한 학사일정의 '하계방학'·'동계방학' 기간 안인가. 학사일정이 없으면 학기 중으로 본다."""
    today = now.strftime("%Y-%m-%d")
    with db.connect() as con:
        rows = con.execute("SELECT content FROM chunk WHERE source_url LIKE '%academic-calendar%' "
                           "AND content LIKE '%방학:%'").fetchall()
    for r in rows:
        for m in _VACATION.finditer(r["content"]):
            if f"{m[1]}-{m[2]}-{m[3]}" <= today <= f"{m[4]}-{m[5]}-{m[6]}":
                return True
    return False


def _bus_table(hits: list[dict], question: str, now: datetime) -> tuple[list[str], list[dict]] | None:
    """가장 비슷한 근거가 통학버스 시간표면, 그 표의 청크를 모두 순서대로 이어 붙여 넘긴다.

    시간표는 행 단위로 여러 청크에 나뉘는데 청크끼리 점수가 거의 같아서(0.61~0.63), 상위 3개만 넘기면
    이른 시간 행이 빠질 수 있다 (예: 두정역 08:00이 있는 청크가 4위로 밀려 10:15를 답함).
    """
    if hits[0]["meta"].get("category") != "통학버스":
        return None
    bus = [h for h in hits if h["meta"].get("category") == "통학버스"]
    day, _ = _day_type(question, now)

    def rank(h):
        header = h["document"].split("\n", 1)[0]
        weekend_page = "주말" in h["meta"].get("title", "")
        page_ok = weekend_page == (day in ("주말", "방학"))
        # 페이지 이름 '(주말·공휴일·방학)' 뒤의 표 이름만 본다. 11/20: 영동 '(방학 기간 …)' 표를 '방학중'이 아니라서
        # 주말 표로 잘못 골라 주말 첫차를 8:00(방학 표)으로 답했다
        table_ok = ("방학" in header.split("] ", 1)[-1]) == (day == "방학")
        return page_ok, table_ok, h["score"]

    best = max(bus, key=rank)
    header = best["document"].split("\n", 1)[0]
    with db.connect() as con:
        rows = con.execute("SELECT content FROM chunk WHERE source_url = ? ORDER BY rowid",
                           (best["meta"].get("source_url"),)).fetchall()
    # 검색에 걸린 표가 오늘에 맞지 않으면, 같은 페이지의 다른 표 중 맞는 표로 바꾼다
    # (11/21 토요일: 검색에 '방학중' 표만 걸려 주말인데 방학 시간표로 답했음)
    if not rank(best)[1]:
        for r in rows:
            h = r["content"].split("\n", 1)[0]
            if ("방학" in h.split("] ", 1)[-1]) == (day == "방학"):
                header = h
                break
    lines = [ln for r in rows if r["content"].split("\n", 1)[0] == header for ln in r["content"].split("\n")[1:]]
    if not lines:
        return None
    return ["\n".join([header] + lines)], [best]


_NEXT_HINTS = ("가장 빠른", "제일 빠른", "빠른 차", "다음", "지금", "방금", "이제", "곧")
_HHMM = re.compile(r"(\d{1,2}):(\d{2})")


# '학교 가는'·'아캠(→아산캠퍼스)'처럼 목적지로도 쓰여서, 다른 정류장이 있으면 무시
_GENERIC_STOPS = ("학교", "아산캠퍼스", "영동캠퍼스")


def _stop_of(key: str, question: str) -> str:
    """시간표 열 이름에서 질문에 나온 정류장 이름을 고른다. 없으면 ''.

    '(등교) 천안터미널 두정역' → '두정역', '아산캠퍼스 출발' → '아산캠퍼스',
    '(등교) 천안터미널 천안 터미널' → '천안터미널' (띄어 쓴 이름은 붙여서도 확인하고 더 긴 쪽을 씀)
    """
    tokens = [t for t in re.sub(r"\(.*?\)", " ", key).split() if t]
    if tokens and tokens[-1] in ("출발", "도착") and len(tokens) > 1:
        tokens = tokens[:-1]
    # '(등교) 천안터미널 천안터미널'처럼 같은 말이 두 번이면 붙이지 않는다 (11/20: '천안터미널천안터미널에서'로 답함)
    joined = "".join(dict.fromkeys(tokens[-2:]))
    names = [n for n in (joined, tokens[-1] if tokens else "") if len(n) >= 2]
    hit = [n for n in names if any(a in question for a in _aliases(n))]
    return max(hit, key=len) if hit else ""


def _aliases(name: str) -> list[str]:
    """'두정역' → ['두정역', '두정'], '천안터미널' → ['천안터미널', '터미널'].

    11/18: '두정에서 가장빠른 통학버스'를 정류장으로 못 알아봐 sLLM이 표를 읽다 운행 종료 칸을 놓쳤다.
    '캠퍼스'는 줄이지 않는다 ('아산'은 캠퍼스 이름으로 거의 모든 질문에 나옴).
    """
    out = [name]
    for suffix in ("역", "아파트", "마트"):
        if name.endswith(suffix) and len(name) - len(suffix) >= 2:
            out.append(name[: -len(suffix)])
    if name.endswith("터미널") and name != "터미널":
        out.append("터미널")
    return out


def _bus_intent(question: str) -> bool:
    return any(w in question for w in ("버스", "통학", "셔틀", "첫차", "막차", "차 시간", "몇 시 차", "빠른 차", "가는 차"))


def _timetable_query(question: str, table: str, now: datetime) -> dict | None:
    """질문에 정류장 이름이 있으면 그 정류장의 시간을 코드로 골라 답할 거리를 만든다 (sLLM을 쓰지 않음).

    2B 모델은 표에서 '현재 시각 이후 가장 가까운 시간'을 고르지 못했다 (07:37·08:10·10:00·13:00 모두 08:00으로 답함).
    목록을 넘겨도 시간을 빠뜨리거나 '남은 운행 없음'을 '정보 없음'으로 바꿔 말했고, 표 전체를 넘기면 19~40초가 걸렸다.
    시간표 조회는 답이 정해진 계산이라 코드가 한다. 종류: next(가장 빠른·다음), first(첫차), last(막차), all(전체 시간).
    """
    # 정류장에 '도착했다'는 질문은 보통 학교로 가는 차를 찾는다. 하교 표현이 있을 때만 하교 시간을 본다.
    direction = "하교" if any(w in question for w in ("하교", "학교에서", "집에", "집으로")) else "등교"
    found, stops = [], set()
    for row in table.split("\n")[1:]:
        segs = [x.split(": ", 1) for x in row.split(" / ") if ": " in x]
        # 영동 시간표는 회차를 '구분'으로 적고 호차가 등교·하교에 두 번 나온다 → '1회차, 1호차'로 한 번씩
        label = ", ".join(dict.fromkeys((v if v.endswith("호차") else f"{v}호차") if k == "호차" else f"{v}회차"
                                         for k, v in segs if k in ("회차", "구분", "호차")))
        for key, val in segs:
            stop = _stop_of(key, question)
            m = _HHMM.fullmatch(val.strip())
            if not m or not stop:
                continue
            if key.startswith(("(등교)", "(하교)")) and not key.startswith(f"({direction})"):
                continue
            found.append((int(m[1]) * 60 + int(m[2]), val.strip(), label, stop))
    stops = {f[3] for f in found}
    if stops - set(_GENERIC_STOPS):
        stops -= set(_GENERIC_STOPS)
        found = [f for f in found if f[3] in stops]
    if not stops:
        return None                      # 질문에 정류장이 없으면 일반 경로(sLLM)로
    found.sort()
    _, explicit_day = _day_type(question, now)
    compact = question.replace(" ", "")          # '가장빠른'처럼 붙여 써도 알아보게
    if "첫차" in compact and "막차" in compact:        # 되묻기 버튼 '첫차·막차'
        mode = "first_last"
    elif "첫차" in compact:
        mode = "first"
    elif "막차" in compact or "마지막" in compact:
        mode = "last"
    elif any(h.replace(" ", "") in compact for h in _NEXT_HINTS):
        mode = "first" if explicit_day else "next"   # 오늘이 아닌 날을 물으면 지금 시각과 비교하지 않음
    else:
        mode = "all"
    cur = now.hour * 60 + now.minute
    return {"mode": mode, "stops": sorted(stops), "direction": direction, "now": now, "found": found,
            "upcoming": [f for f in found if f[0] >= cur]}


def _table_name(header: str) -> str:
    """'[아산캠퍼스 통학버스 (학기 중)] 1,2호차 학기 중(월~금) 운행노선표 (45인승) (천안시내 …)' → 앞의 두 부분만"""
    name, _, rest = header.strip("[").partition("] ")
    rest = re.sub(r"\s*\([^)]*(운행|도착시간)[^)]*\)\s*$", "", rest)
    # 페이지 이름 '(주말·공휴일·방학)' 때문에 주말 표도 방학 표처럼 보였다 (11/21) → 표 이름에 맞는 말만 남긴다
    name = re.sub(r"\s*\(주말·공휴일·방학\)", "", name)
    return f"{name} {rest}".strip()


def _lab(label: str) -> str:
    """' (2회차, 2호차)'. 회차·호차가 없는 시간표면 괄호를 쓰지 않는다 (예전엔 '8:00 ()'로 나왔음)."""
    return f" ({label})" if label else ""


def _timetable_answer(q: dict, header: str) -> str:
    stop, d, now, found, up = "·".join(q["stops"]), q["direction"], q["now"], q["found"], q["upcoming"]
    if not found:
        text = f"{stop} {d} 시간이 이 시간표에 없습니다."
    # 11/21 사용자 요청: 한 줄에 다 붙어 있어 읽기 어려움 → 첫 줄에 답, 나머지는 한 줄에 하나씩
    elif q["mode"] == "next" and up:
        # 11/18 사용자 요청: '지금(03:13) 기준으로' 같은 현재 시각 표시는 빼고 답만 보여줌
        text = f"{stop}에서 가장 빠른 {d} 버스는 {up[0][1]}{_lab(up[0][2])}입니다."
        if len(up) > 1:
            text += f"\n· 다음 차: {up[1][1]}{_lab(up[1][2])}"
    elif q["mode"] == "next":
        text = (f"오늘({_WEEKDAYS[now.weekday()]}요일) {stop} {d} 버스는 모두 끝났습니다."
                f"\n· 이 시간표의 첫차: {found[0][1]}{_lab(found[0][2])}")
    elif q["mode"] == "first":
        text = f"{stop}에서 {d} 첫차는 {found[0][1]}{_lab(found[0][2])}입니다."
        if len(found) > 1:
            text += f"\n· 그다음 차: {found[1][1]}{_lab(found[1][2])}"
    elif q["mode"] == "last":
        text = f"{stop}에서 {d} 막차는 {found[-1][1]}{_lab(found[-1][2])}입니다."
    elif q["mode"] == "first_last":
        text = (f"{stop} {d} 첫차·막차입니다.\n· 첫차: {found[0][1]}{_lab(found[0][2])}"
                f"\n· 막차: {found[-1][1]}{_lab(found[-1][2])}")
    else:
        times = list(dict.fromkeys(f[1] for f in found))   # 같은 시간이 여러 호차로 나오면 한 번만
        groups = {"오전": [], "오후": [], "저녁": []}
        for t in times:
            h = int(t.split(":")[0])
            groups["오전" if h < 12 else "오후" if h < 18 else "저녁"].append(t)
        text = f"{stop} {d} 버스 시간입니다." + "".join(
            f"\n· {k}: {', '.join(v)}" for k, v in groups.items() if v)
    return text + f"\n\n기준: {_table_name(header)}\n도착 시간은 교통 상황에 따라 달라질 수 있습니다."


def register_pending(question: str, category: str | None, campus: str | None, qvec: list[float]) -> int:
    """비슷한 질문이 이미 대기 중이면 질문 수만 올리고, 아니면 새로 등록한다."""
    masked = db.mask(question)[:200]
    ts = db.now()
    with db.connect() as con:
        row, score = _nearest(con, "SELECT pending_id, vec FROM pending_question WHERE status = '대기'", qvec)
        if row is not None and score >= config.SAME_QUESTION:
            con.execute("UPDATE pending_question SET question_count = question_count + 1, last_asked_at = ? "
                        "WHERE pending_id = ?", (ts, row["pending_id"]))
            return row["pending_id"]
        cur = con.execute(
            "INSERT INTO pending_question (question, category, campus, first_asked_at, last_asked_at, expires_at, vec) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", (masked, category, campus, ts, ts, db.expires_from(ts), _blob(qvec)))
        return cur.lastrowid


_DATE = re.compile(r"(20\d{2})\s*[.\-년]\s*(\d{1,2})\s*[.\-월]\s*(\d{1,2})")
_WHEN = ("언제", "날짜", "기간", "일정", "며칠", "몇 일", "마감", "까지", "시작")


def _dates(text: str) -> list[str]:
    out = []
    for y, m, d in _DATE.findall(text):
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            out.append(f"{y}-{int(m):02d}-{int(d):02d}")
    return out


def _rerank(question: str, hits: list[dict], now: datetime) -> list[dict]:
    """날짜를 묻는 질문이면 이미 지난 일정은 내리고 다가오는 일정은 올린다. 대학원 자료는 '대학원'을 물을 때만.

    11/18: 사이트 전체를 넣었더니 '학위수여식 언제?'에 지난 2025학년도 행사 페이지가 1위로 올라오고,
    학부 질문에 대학원 학칙·등록 안내가 근거로 들어갔다.
    """
    if "대학원" not in question:
        hits = [h for h in hits if not h["meta"].get("title", "").startswith("대학원:")]
    if not any(w in question for w in _WHEN):
        return hits
    # 반년 넘게 지난 일정만 내린다. 올해 이미 지난 일정(하계 계절학기, 2학기 수강정정)을 묻는 질문도 있어서
    today, stale = now.strftime("%Y-%m-%d"), (now - timedelta(days=180)).strftime("%Y-%m-%d")

    def adjusted(h):
        ds = _dates(h["meta"].get("title", "") + " " + h["document"][:400])
        if not ds:
            return h["score"]
        if max(ds) >= today:
            return h["score"] + 0.03
        return h["score"] - 0.08 if max(ds) < stale else h["score"]
    return sorted(hits, key=adjusted, reverse=True)


def _with_club_summary(hits: list[dict]) -> list[dict]:
    """동아리 하나하나의 조각이 걸리면, 분과별 동아리 목록(요약 조각)을 맨 앞에 붙인다.

    11/19: '운동 동아리 뭐 있어?'에 동아리 조각 3개만 넘어가 족구동아리가 빠졌다. 목록 질문은 요약이 있어야 다 답한다.
    """
    if not any(h["meta"].get("title", "").startswith("동아리:") for h in hits[:3]):
        return hits
    if any(h["meta"].get("title") == "동아리현황" for h in hits[:3]):
        return hits
    with db.connect() as con:
        row = con.execute("SELECT chunk_id, title, content, source_url, menu_path, collected_at, campus, category "
                          "FROM chunk WHERE title = '동아리현황' LIMIT 1").fetchone()
    if row is None:
        return hits
    summary = {"id": row["chunk_id"], "score": hits[0]["score"], "document": row["content"],
               "meta": {"title": row["title"], "category": row["category"], "campus": row["campus"] or "공통",
                        "source_url": row["source_url"], "menu_path": row["menu_path"] or "",
                        "collected_at": row["collected_at"]}}
    return [summary] + [h for h in hits if h["id"] != row["chunk_id"]]


def _ranked_hits(qvec: list[float], where: dict | None, question: str = "") -> list[dict]:
    """공식 자료(공지·학사일정·통학버스·동아리·FAQ)를 먼저, 학생 Q&A는 최대 1개만 붙인다.

    11/18: Q&A를 넣었더니 질문 모양이 비슷한 Q&A가 상위 1~3위를 다 차지해서,
    날짜가 적힌 학사일정·공지가 sLLM에 못 갔다 (계절학기 기간, 조기졸업 전화번호 등).
    """
    def search(cond):
        w = {"$and": [where, cond]} if where else cond
        hits = [h for h in index.search("chunks", qvec, config.TOP_K * 2, w) if h["score"] >= config.MIN_SCORE]
        return _rerank(question, hits, _now())[:config.TOP_K]

    official = search({"category": {"$ne": "Q&A"}})
    official = _with_club_summary(official)
    qna = search({"category": "Q&A"})
    top = official[:config.CONTEXT_K - 1] + qna[:1]
    rest = official[config.CONTEXT_K - 1:] + qna[1:]
    return top + rest           # 앞에서부터 CONTEXT_K개가 sLLM에 넘어감


_CONTEST_WORDS = ("공모전", "경진대회", "콘테스트", "공모", "해커톤")
_CONTEST_TITLE = ("공모전", "경진대회", "콘테스트", "대회")     # 목록에 넣을 제목 ('기관 공모', '논문 공모'는 학생 공모전이 아님)
_MONTH_DAY = re.compile(r"(?<!\d)(\d{1,2})월\s*(\d{1,2})일")
_LIST_WORDS = ("요즘", "진행", "모집", "지금", "현재", "뭐있", "있어", "있나", "목록", "알려", "종류", "어떤", "마감", "임박", "빠른", "언제")
_CONTEST_STOP = set("공모전 경진대회 콘테스트 공모 요즘 하는 지금 현재 진행 진행중 중인 모집 모집중 뭐 뭐가 있어 있어? 있나 있나요 "
                    "알려줘 알려줘봐 알려 주세요 목록 종류 어떤 거 것 좀 학교 우리 참여 참가 할 수 있는".split())
_ORDER_WORDS = set("가장 제일 빠른 빠른순 날짜 마감 마감일 임박 곧 순서 먼저 언제 언제까지 기간 일정 최근 새로운".split())
_SOONEST = ("가장빠른", "제일빠른", "마감임박", "곧마감", "빠른순", "마감순", "가장먼저", "제일먼저")


def _contest_intent(question: str) -> bool:
    """공모전 목록을 묻는가. '공모전'만 보낸 것(학과를 고른 뒤 다시 오는 질문 포함)도 목록으로 본다."""
    compact = question.replace(" ", "")
    if not any(w in compact for w in _CONTEST_WORDS):
        return False
    only = all(t in clarifier.FILLER or any(w in t for w in _CONTEST_WORDS) for t in clarifier._tokens(question))
    return only or any(w in compact for w in _LIST_WORDS)


def _contest_deadlines(campus: str | None, today: str) -> dict:
    """학교 공지(학과 사이트 포함) 중 날짜가 아직 안 지난 공모전. {이름: (마지막 날짜, 행, 올린 곳 목록)}"""
    cond = " OR ".join("title LIKE ?" for _ in _CONTEST_TITLE)
    with db.connect() as con:
        rows = con.execute(f"SELECT title, content, source_url, menu_path, collected_at, posted_at, campus FROM chunk "
                           f"WHERE ({cond})", [f"%{w}%" for w in _CONTEST_TITLE]).fetchall()
    found = {}
    for r in rows:
        if campus and r["campus"] not in (None, "", "공통", campus):
            continue
        name = r["title"].split(": ", 1)[-1].strip()          # '미래자동차학과: 제목' → '제목' (학과마다 같은 공지)
        other = {"아산": "영동", "영동": "아산"}.get(campus or "")
        if other and (f"({other})" in name or f"{other}캠" in name):   # 제목에 다른 캠퍼스가 적힌 공지는 뺀다
            continue
        year = (r["posted_at"] or today)[:4]                    # '11월 30일(월)까지'처럼 연도가 없으면 게시 연도로 본다
        deadline, exact = _apply_deadline(r["content"][:2000], year)
        if deadline is None:                                    # 접수·기간 줄이 없으면 공지 안의 가장 늦은 날짜 (발표일일 수 있음)
            text = r["title"] + " " + r["content"][:1500]
            deadline = max(_dates(text) + _loose_dates(text, year), default=None)
        if not deadline or deadline < today:
            continue
        site = r["title"].split(": ", 1)[0] if ": " in r["title"] else "학교"
        if name in found:
            found[name][2].append(site)
        else:
            found[name] = (deadline, r, [site], exact)
    return found


_APPLY = re.compile(r"접수|신청|모집|응모")
_PERIOD = re.compile(r"기간")
_MD_DOT = re.compile(r"(?<![\d.])(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*(?=\()")     # '10. 30.(금)', '11.13.(금)'


def _loose_dates(text: str, year: str) -> list[str]:
    """연도 없이 쓴 날짜 ('11월 30일', '10. 30.(금)')를 게시 연도로 읽는다."""
    out = []
    for m, d in _MONTH_DAY.findall(text) + _MD_DOT.findall(text):
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            out.append(f"{year}-{int(m):02d}-{int(d):02d}")
    return out


def _apply_deadline(content: str, year: str) -> tuple[str | None, bool]:
    """공모전 공지에서 접수 마감일을 찾는다. (날짜, 접수 마감이 맞는가)

    11/21: 공지 안의 가장 늦은 날짜(시상식·결과 발표)를 마감으로 봐서, 접수가 끝난 공모전을 '모집 중'으로 보여 줬다
    (AI시스템트레이딩: 시상식 11.30 / 안산시 숏폼: 접수 10.30, 발표 12.4 / 학습법: 신청 10.23, 최종 제출 11.30).
    1) '접수·신청·모집·응모'가 든 줄의 날짜 ('2026.9.28.~'처럼 끝이 없는 줄은 건너뜀)
    2) 없으면 '기간'이 든 줄 (예: 대회 기간 10.19~11.13)
    """
    for pattern in (_APPLY, _PERIOD):
        ends = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not pattern.search(line):
                continue
            # '3. 접수기간:' 다음 줄에 날짜가 오는 공지가 있어 다음 줄까지 본다
            if not (_dates(line) + _loose_dates(line, year)) and i + 1 < len(lines):
                line = line + " " + lines[i + 1]
            if re.search(r"~\s*$", line.strip()):         # '2026.9.28.~'처럼 끝이 없는 기간
                continue
            ds = _dates(line) + _loose_dates(line, year)
            if ds:
                ends.append(max(ds))
        if ends:
            return min(ends), pattern is _APPLY       # 신청과 제출이 따로 있으면 먼저 오는 신청 마감
    return None, False


def _contest_list(question: str, campus: str | None, now: datetime, dept: str | None) -> tuple[str, list[dict]] | None:
    """공모전 목록 질문에 학과에 맞는 것부터 답한다. 학교 공지 + 충청남도 공모전 API + 네이버 뉴스 (external.py).

    11/19: 이런 질문은 특정 공지와 문장이 닮지 않아 검색 점수가 낮고 근거없음이 됐다 → 코드로 모은다.
    11/20: 학과마다 관련 공모전이 달라서 학과를 받아(되묻기, clarifier.py) 순서를 정한다.
    - 학과 추천: 그 학과 사이트에 올라온 공모전, 제목·본문 앞부분에 학과 키워드(departments.py)가 든 공모전
    - 누구나 참가할 수 있는 다른 공모전: 나머지
    질문에 주제어가 있으면(예: '동아리 공모전') 그 말이 든 것만 고르고, 없으면 그렇다고 말한 뒤 전체를 보여준다.
    """
    today = now.strftime("%Y-%m-%d")
    found = _contest_deadlines(campus, today)
    dept = None if dept in (departments.ALL, departments.MORE) else dept
    kw = departments.keywords(dept)
    # 11/21: '가장 빠른 공모전 날짜좀'의 '가장 빠른 날짜좀'을 주제어로 잘못 보고 '관련 공모전이 없다'고 답했다.
    # 순서·날짜를 묻는 말과 끝에 붙은 '좀'은 주제어에서 뺀다
    words = [re.sub(r"좀$", "", w) for w in re.findall(r"[가-힣A-Za-z0-9]+", question)]
    words = [w for w in words if w not in _CONTEST_STOP and not any(w.startswith(o) for o in _ORDER_WORDS) and len(w) >= 2
             and not (dept and (w in dept or dept in w))]
    soonest = any(w in question.replace(" ", "") for w in _SOONEST)
    picked = {k: v for k, v in found.items() if any(w in k for w in words)} if words else found
    # 질문 문장은 보내지 않고 주제어(없으면 학과 키워드 두 개)만 외부 검색에 보낸다
    news = external.contest_news(words or list(kw[:2]), now)
    region = external.chungnam_contests(now)
    sites = external.site_contests(now)          # 위비티·콘테스트코리아 IT·SW·과학 공모전 (11/21)
    if words:
        region = [c for c in region if any(w in c["title"] for w in words)]
        # 영어 제목도 찾게 한다 ('INNO-CODER AI HACKATHON')
        alias = {"해커톤": "hackathon", "인공지능": "ai", "로봇": "robot", "게임": "game"}
        sites = [c for c in sites if any(w.lower() in c["title"].lower() or alias.get(w, "\0") in c["title"].lower()
                                         for w in words)]
    if not found and not news and not region and not sites:
        return None

    def fits(name: str, row=None, sites=()) -> bool:
        # 제목에서만 보고, '[홍보]' 같은 말머리는 뺀다. 본문까지 보면 '대외홍보팀' 같은 부서 이름에 걸렸다
        head = re.sub(r"\[[^\]]*\]", " ", name)
        # 'IT'·'SW'처럼 짧은 영어 키워드는 대소문자를 그대로 본다 ('Digital'의 'it'에 걸리지 않게)
        return bool(dept) and (dept in sites or any(
            (k in head) if (k.isascii() and len(k) <= 3) else (k.lower() in head.lower()) for k in kw))

    parts, sources = [], []
    if words and not picked:
        parts.append(f"'{' '.join(words)}' 관련 공모전은 학교 공지에 없습니다.")
        picked = found
    school = sorted(picked.items(), key=lambda kv: kv[1][0])
    mine = [(n, v) for n, v in school if fits(n, v[1], v[2])]
    rest = [(n, v) for n, v in school if not fits(n, v[1], v[2])]
    region_mine = [c for c in region if fits(c["title"])]
    region_rest = [c for c in region if not fits(c["title"])]

    # 위비티·콘테스트코리아 공모전 (11/21). 학과를 골랐으면 학과 키워드가 제목이나 위비티 분야
    # (주최 측이 공모전마다 고른 '웹/모바일/IT' 등)에 든 것만. 콘테스트코리아 분야는 '요리/뷰티/배우/오디션'처럼
    # 여러 분야를 묶은 큰 갈래라서 쓰지 않는다 (호텔조리에 아이돌 오디션이 걸렸음).
    # 제목과 분야 둘 다 맞는 것 → 제목만 → 분야만 순서, 그 안에서 마감 빠른 순 ('AI 영상 공모전'보다 'AI 해커톤'이 먼저)
    if dept:
        def score(c):
            field = c.get("field", "") if c["site"] == "위비티" else ""
            return fits(c["title"]) * 2 + (bool(field) and fits(field))
        pick = sorted((c for c in sites if score(c)), key=lambda c: (-score(c), c["deadline"]))
    else:
        pick = sites

    def site_line(c):
        # 주최가 여러 곳이면 첫 곳만, 길면 줄인다 ('(재)운당나눔재단, (재)울산창조경제혁신센터' → '(재)운당나눔재단 외')
        host = re.split(r"\s*[,·×]\s*", c["host"])[0] if c["host"] else ""
        host = (host[:14] + "…" if len(host) > 15 else host) + (" 외" if host != c["host"].strip() and host else "")
        return f"· {c['title']} (~{c['deadline'][5:7]}.{c['deadline'][8:10]}{', ' + host if host else ''})"
    ext = ""
    if pick:
        ext = (f"{dept + '에 맞는 외부 공모전' if dept else '외부 공모전'}입니다 (위비티·콘테스트코리아).\n"
               + "\n".join(site_line(c) for c in pick[:20])
               + (f"\n외 {len(pick) - 20}건은 출처의 공모전 목록에서 볼 수 있습니다." if len(pick) > 20 else ""))

    def school_line(n, v):
        # 접수 줄에서 찾은 날짜면 '접수 ~', 아니면(발표일일 수도 있음) '일정 ~'
        return f"· {n} ({'접수' if v[3] else '일정'} ~{v[0][5:7]}.{v[0][8:10]})"

    def region_line(c):
        return (f"· {c['title']} (충청남도, 접수 {c['start'][5:7]}.{c['start'][8:10]}~"
                f"{c['deadline'][5:7]}.{c['deadline'][8:10]})")

    if soonest:                             # '가장 빠른·마감 임박' → 날짜가 가장 가까운 것 하나를 먼저 말한다
        cands = ([(v[0], n) for n, v in school] + [(c["deadline"], c["title"]) for c in region]
                 + [(c["deadline"], c["title"]) for c in sites if not dept or fits(c["title"])])
        if cands:
            d, n = min(cands)
            parts.append(f"마감이 가장 가까운 공모전은 '{n}'입니다 (~{d[5:7]}.{d[8:10]}).")
    if dept:
        lines = [school_line(n, v) for n, v in mine[:5]] + [region_line(c) for c in region_mine]
        if lines:
            parts.append(f"{dept} 추천 공모전입니다.\n" + "\n".join(lines))
        elif not pick:
            parts.append(f"{dept}에 딱 맞는 공모전은 지금 학교 공지와 외부 공모전 목록에 없습니다.")
        if ext:                             # 학과에 맞는 외부 공모전은 학교 추천 바로 다음에
            parts.append(ext)
        others = [school_line(n, v) for n, v in rest[:4]] + [region_line(c) for c in region_rest[:2]]
        if others:
            parts.append("누구나 참가할 수 있는 다른 공모전입니다.\n" + "\n".join(others))
    else:
        lines = [school_line(n, v) for n, v in school[:6]] + [region_line(c) for c in region]
        if lines:
            parts.append("지금 모집 중인 공모전입니다.\n" + "\n".join(lines))
        if ext:
            parts.append(ext)
    sources += [{"title": v[1]["title"], "kind": "공지", "source_url": v[1]["source_url"], "menu_path": v[1]["menu_path"],
                 "collected_at": v[1]["collected_at"], "label": v[1]["title"]} for _, v in (mine + rest)[:2]]
    if region:
        sources.append({"title": "충청남도 공모전 일정", "kind": "외부 API", "source_url": region[0]["url"],
                        "menu_path": None, "collected_at": None, "label": "출처: 충청남도 (공공누리)"})
    if pick:
        sources += [{"title": "위비티 공모전", "kind": "외부 사이트",
                     "source_url": "https://www.wevity.com/?c=find&s=1&gub=1", "menu_path": None,
                     "collected_at": None, "label": "위비티 공모전 목록"},
                    {"title": "콘테스트코리아 공모전", "kind": "외부 사이트",
                     "source_url": "https://www.contestkorea.com/sub/list.php?int_gbn=1",
                     "menu_path": None, "collected_at": None, "label": "콘테스트코리아 공모전 목록"}]
    if news:
        parts.append("외부 공모전 소식 (네이버 뉴스)입니다.\n" +
                     "\n".join(f"· {n['title']} ({n['date']} 기사)" for n in news))
        sources += [{"title": n["title"], "kind": "외부 검색", "source_url": n["url"], "menu_path": None,
                     "collected_at": None, "label": f"네이버 뉴스 · {n['title'][:30]}"} for n in news[:2]]
    parts.append("자세한 접수 기간과 조건은 출처에서 확인해 주세요.")
    return "\n\n".join(parts), sources


# 학생들이 쓰는 줄임말을 풀어서 검색·FAQ·규칙이 알아보게 한다 (11/20: '통버 무료임?'이 통학버스 FAQ에 안 걸림)
_ABBR = [(re.compile(r"통버"), "통학버스"), (re.compile(r"아캠"), "아산캠퍼스"), (re.compile(r"영캠"), "영동캠퍼스"),
         (re.compile(r"셔틀(?!버스)"), "셔틀버스"), (re.compile(r"계절(?!학기)"), "계절학기")]
# 서로 다른 대상: 질문에 한쪽이 있는데 FAQ 질문에 그 말이 없으면 FAQ를 쓰지 않는다
# (11/20: '시내버스 요금 얼마야?'가 '통학버스 요금은 얼마인가요?' FAQ에 0.82로 걸려 '무료'라고 답할 뻔함)
_DISTINCT = [("시내버스", "통학버스", "셔틀버스", "고속버스"), ("국가장학금", "교내장학금"), ("아산", "영동")]


def _normalize(question: str) -> str:
    for pat, full in _ABBR:
        question = pat.sub(full, question)
    return question


# 무엇을 묻는가. 질문과 FAQ가 서로 다른 것을 물으면 FAQ를 쓰지 않는다
# (11/20: '통학버스 시간표'가 '통학버스 요금은 얼마인가요?' FAQ에 걸려 '무료입니다'로 답함)
_ASPECTS = {
    "요금": ("요금", "무료", "돈", "비용", "얼마", "유료", "가격", "금액", "수수료"),
    "시간": ("시간표", "시간", "몇 시", "몇시", "첫차", "막차", "배차", "운행", "다녀", "다니"),
    "날짜": ("언제", "기간", "날짜", "며칠", "마감", "일정"),
    "장소": ("어디", "장소", "위치", "몇 층", "어느 건물"),
    "연락처": ("전화", "연락처", "번호", "이메일", "문의처"),
    "방법": ("방법", "어떻게", "절차", "서류", "신청서"),
    "자격": ("자격", "대상", "조건", "기준"),
}


def _aspects(text: str) -> set[str]:
    return {name for name, words in _ASPECTS.items() if any(w in text for w in words)}


def _faq_conflicts(question: str, faq_question: str) -> bool:
    for group in _DISTINCT:
        asked = {w for w in group if w in question}
        if asked and not asked & {w for w in group if w in faq_question} and any(w in faq_question for w in group):
            return True
    q_asp, f_asp = _aspects(question), _aspects(faq_question)
    return bool(q_asp and f_asp and not q_asp & f_asp)


def ask(question: str, category: str | None = None, campus: str | None = None,
        department: str | None = None) -> dict:
    t0 = time.perf_counter()
    question = _normalize(question.strip())
    qvec = index.embed([question])[0]
    result = {"answer_type": "근거없음", "answer": NOT_FOUND_ANSWER, "sources": [], "schedule": None,
              "clarify": None, "pending_registered": False}
    answered_by, contexts = None, []          # 기록용: 누가 답했나(llm·timetable), sLLM에 넘긴 근거

    # 되묻기를 FAQ보다 먼저 본다 (11/20: '통학버스' 한 단어에 요금 FAQ '무료입니다'로 답했음)
    clarify = clarifier.check(question, campus, department)      # 애매한 질문은 먼저 되묻는다 (FR-027)
    if clarify:
        result.update(answer_type="되묻기", answer=clarify["question"], clarify=clarify)
    else:
        with db.connect() as con:
            faq, score = _nearest(con, "SELECT * FROM faq", qvec)
            if faq is not None and score >= config.FAQ_SCORE and not _faq_conflicts(question, faq["question"]):
                con.execute("UPDATE faq SET ask_count = ask_count + 1 WHERE faq_id = ?", (faq["faq_id"],))
                result.update(answer_type="FAQ", answer=faq["answer"], sources=[{
                    "title": faq["question"], "kind": "관리자 등록 답변", "source_url": None, "menu_path": None,
                    "collected_at": faq["created_at"], "label": f"관리자 등록 답변 · {faq['created_at'][:10]}"}])

    # 학식 메뉴는 오늘·내일·요일을 코드가 계산해 고른다 (11/20: 금요일에 화요일 메뉴를 답했음)
    if result["answer_type"] == "근거없음" and cafeteria.is_menu_question(question):
        menu = cafeteria.answer(question, campus, _now())
        if menu:
            answered_by = "cafeteria"
            # 그날 식단이 없으면(주말·아직 안 올라옴) 근거없음으로 알리되, 답변 대기에는 올리지 않는다
            result.update(answer_type="문서" if menu[1] else "근거없음", answer=menu[0], sources=[{
                "title": "학교 구내식당", "kind": "학교 홈페이지", "source_url": "https://www.u1.ac.kr/u1/life/cafeteria.do",
                "menu_path": "홈 > 대학생활 > 학교 구내식당", "collected_at": None, "label": "유원대: 학교 구내식당"}])

    if result["answer_type"] == "근거없음" and _contest_intent(question):
        # 질문에 적힌 학과가 우선. 직접 적은 학과는 줄임말도 알아본다 (예: '간호' → 간호학과)
        dept = departments.find_in(question) or (department and departments.find_in(department)) or department
        contest = _contest_list(question, campus, _now(), dept)
        if contest:
            result.update(answer_type="문서", answer=contest[0], sources=contest[1])

    if result["answer_type"] == "근거없음" and answered_by is None:
        where = _campus_filter(campus)
        if category:
            cond = {"category": category}
            where = {"$and": [where, cond]} if where else cond
        hits = _ranked_hits(qvec, where, question)
        if (not hits or hits[0]["meta"].get("category") != "통학버스") and _bus_intent(question):
            # 버스 질문인데 일반 검색에서 시간표가 기준값을 못 넘으면, 통학버스 청크만 따로 찾는다.
            # 시간표에 실제로 있는 정류장이 질문에 나올 때만 쓴다 (아래 _timetable_query가 확인)
            cond = {"category": "통학버스"}
            bus_where = {"$and": [_campus_filter(campus), cond]} if _campus_filter(campus) else cond
            bus_hits = index.search("chunks", qvec, config.TOP_K, bus_where)
            table = _bus_table(bus_hits, question, _now()) if bus_hits else None
            if table and _timetable_query(question, table[0][0], _now()):
                hits = bus_hits
        if hits:
            now = _now()
            top = hits[:config.CONTEXT_K]
            contexts, used = [h["document"] for h in top], top
            table = _bus_table(hits, question, now)
            tq = None
            if table:
                contexts, used = table
                tq = _timetable_query(question, contexts[0], now)
            if tq:
                text = _timetable_answer(tq, contexts[0].split("\n", 1)[0])
                answered_by = "timetable"
            elif config.USE_LLM:
                text = llm.answer(question, contexts, _now_text(now))
                answered_by = "llm"
            else:
                text = contexts[0][:400]
            if text and not llm.is_not_found(text):
                result.update(answer_type="문서", answer=text, sources=_sources_from_chunks(used))
        if result["answer_type"] == "근거없음":
            register_pending(question, category, campus, qvec)
            result["pending_registered"] = True

    result["answer"] = readable.tidy(result["answer"])     # 모든 답: 목록 기호 통일, 긴 문단 줄 나눔 (11/21)
    result["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    # 답변 피드백(관리 웹 '답변 고치기')과 파인튜닝 데이터에 쓰려고, sLLM이 본 근거와 답을 함께 남긴다.
    # 근거는 학교 공지 원문이고, 질문·답은 전화번호·학번 형태를 가린다.
    log_ctx = json.dumps({"by": answered_by, "contexts": contexts if answered_by == "llm" else []}, ensure_ascii=False)
    with db.connect() as con:
        cur = con.execute("INSERT INTO query_log (question, category, campus, answer_type, response_ms, created_at, "
                          "answer, contexts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (db.mask(question)[:200], category, campus, result["answer_type"], result["elapsed_ms"],
                           db.now(), db.mask(result["answer"])[:2000], log_ctx))
        result["log_id"] = cur.lastrowid
    return result


def add_faq(pending_id: int, question: str, answer: str, category: str, campus: str | None) -> int:
    """관리자 답변을 FAQ로 저장하고 바로 검색에 쓰이게 한다 (FR-029, PER-010). 승인 단계 없음."""
    vec = _blob(index.embed([question])[0])
    ts = db.now()
    with db.connect() as con:
        cur = con.execute("INSERT INTO faq (pending_id, question, answer, category, campus, created_at, indexed_at, vec) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (pending_id, question, answer, category, campus, ts, ts, vec))
        con.execute("UPDATE pending_question SET status = '답변완료', handled_at = ? WHERE pending_id = ?",
                    (ts, pending_id))
        return cur.lastrowid


def mark_not_mine(pending_id: int):
    with db.connect() as con:
        con.execute("UPDATE pending_question SET status = '담당아님', handled_at = ? WHERE pending_id = ?",
                    (db.now(), pending_id))
