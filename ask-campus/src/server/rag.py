"""질문 하나를 처리한다 (API 명세 1-2 서버 처리 순서).

1) FAQ(학과 조교 답변)에서 거의 같은 질문을 찾으면 그 답변을 그대로 돌려줌
2) 아니면 청크를 검색해 기준 이상이면 sLLM이 근거만으로 답변
3) 근거가 없거나 sLLM이 "찾을 수 없습니다"라고 하면 답변 대기에 자동 등록 (FR-005, FR-028)

청크는 Chroma에서, FAQ·답변 대기는 SQLite vec 열에서 찾는다 (db.py 설명 참고).
"""
import re
import time
from datetime import datetime

import numpy as np

from . import config, db, index, llm

SOURCE_GAP = 0.04          # 출처로 보여 줄 근거의 점수 차이 한도

NOT_FOUND_ANSWER = ("해당 정보를 찾을 수 없습니다. 아직 답을 모르는 질문이라 학과 조교에게 전달했어요. "
                    "답변이 등록되면 같은 질문에 바로 답해 드릴게요.")


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
    return ("주말" if now.weekday() >= 5 else "평일"), False   # 방학 기간은 아직 모르므로 학기 중으로 본다


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
        table_ok = ("방학중" in header) == (day == "방학")
        return page_ok, table_ok, h["score"]

    best = max(bus, key=rank)
    header = best["document"].split("\n", 1)[0]
    with db.connect() as con:
        rows = con.execute("SELECT content FROM chunk WHERE source_url = ? ORDER BY rowid",
                           (best["meta"].get("source_url"),)).fetchall()
    lines = [ln for r in rows if r["content"].split("\n", 1)[0] == header for ln in r["content"].split("\n")[1:]]
    if not lines:
        return None
    return ["\n".join([header] + lines)], [best]


_NEXT_HINTS = ("가장 빠른", "제일 빠른", "빠른 차", "다음", "지금", "방금", "이제", "곧")
_HHMM = re.compile(r"(\d{1,2}):(\d{2})")


_GENERIC_STOPS = ("학교",)      # '학교 가는'처럼 목적지로도 쓰여서, 다른 정류장이 있으면 무시


def _stop_of(key: str, question: str) -> str:
    """시간표 열 이름에서 질문에 나온 정류장 이름을 고른다. 없으면 ''.

    '(등교) 천안터미널 두정역' → '두정역', '아산캠퍼스 출발' → '아산캠퍼스',
    '(등교) 천안터미널 천안 터미널' → '천안터미널' (띄어 쓴 이름은 붙여서도 확인하고 더 긴 쪽을 씀)
    """
    tokens = [t for t in re.sub(r"\(.*?\)", " ", key).split() if t]
    if tokens and tokens[-1] in ("출발", "도착") and len(tokens) > 1:
        tokens = tokens[:-1]
    names = [n for n in ("".join(tokens[-2:]), tokens[-1] if tokens else "") if len(n) >= 2 and n in question]
    return max(names, key=len) if names else ""


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
        label = ", ".join(v if k == "호차" else f"{v}회차" for k, v in segs if k in ("회차", "호차"))
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
    if "첫차" in question or "첫 차" in question:
        mode = "first"
    elif "막차" in question or "마지막" in question:
        mode = "last"
    elif any(h in question for h in _NEXT_HINTS):
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
    return f"{name} {rest}".strip()


def _timetable_answer(q: dict, header: str) -> str:
    stop, d, now, found, up = "·".join(q["stops"]), q["direction"], q["now"], q["found"], q["upcoming"]
    if not found:
        text = f"{stop} {d} 시간이 이 시간표에 없습니다."
    elif q["mode"] == "next" and up:
        text = f"지금({now:%H:%M}) 기준으로 {stop}에서 가장 빠른 {d} 버스는 {up[0][1]} ({up[0][2]})입니다."
        if len(up) > 1:
            text += f" 다음 차는 {up[1][1]} ({up[1][2]})입니다."
    elif q["mode"] == "next":
        text = (f"오늘({_WEEKDAYS[now.weekday()]}요일) {stop} {d} 버스는 모두 끝났습니다. "
                f"이 시간표의 첫차는 {found[0][1]} ({found[0][2]})입니다.")
    elif q["mode"] == "first":
        text = f"{stop}에서 {d} 첫차는 {found[0][1]} ({found[0][2]})입니다."
        if len(found) > 1:
            text += f" 그다음 차는 {found[1][1]} ({found[1][2]})입니다."
    elif q["mode"] == "last":
        text = f"{stop}에서 {d} 막차는 {found[-1][1]} ({found[-1][2]})입니다."
    else:
        times = list(dict.fromkeys(f[1] for f in found))   # 같은 시간이 여러 호차로 나오면 한 번만
        more = f" 외 {len(times) - 20}회" if len(times) > 20 else ""
        text = f"{stop} {d} 버스 시간은 {', '.join(times[:20])}{more}입니다."
    return text + f"\n기준 시간표: {_table_name(header)}. 도착 시간은 교통 상황에 따라 달라질 수 있습니다."


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


def ask(question: str, category: str | None = None, campus: str | None = None) -> dict:
    t0 = time.perf_counter()
    question = question.strip()
    qvec = index.embed([question])[0]
    result = {"answer_type": "근거없음", "answer": NOT_FOUND_ANSWER, "sources": [], "schedule": None,
              "clarify": None, "pending_registered": False}

    with db.connect() as con:
        faq, score = _nearest(con, "SELECT * FROM faq", qvec)
        if faq is not None and score >= config.FAQ_SCORE:
            con.execute("UPDATE faq SET ask_count = ask_count + 1 WHERE faq_id = ?", (faq["faq_id"],))
            result.update(answer_type="FAQ", answer=faq["answer"], sources=[{
                "title": faq["question"], "kind": "학과 조교 답변", "source_url": None, "menu_path": None,
                "collected_at": faq["created_at"], "label": f"학과 조교 답변 · {faq['created_at'][:10]}"}])

    if result["answer_type"] != "FAQ":
        where = _campus_filter(campus)
        if category:
            cond = {"category": category}
            where = {"$and": [where, cond]} if where else cond
        hits = [h for h in index.search("chunks", qvec, config.TOP_K, where) if h["score"] >= config.MIN_SCORE]
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
            elif config.USE_LLM:
                text = llm.answer(question, contexts, _now_text(now))
            else:
                text = contexts[0][:400]
            if text and not llm.is_not_found(text):
                result.update(answer_type="문서", answer=text, sources=_sources_from_chunks(used))
        if result["answer_type"] == "근거없음":
            register_pending(question, category, campus, qvec)
            result["pending_registered"] = True

    result["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    with db.connect() as con:
        con.execute("INSERT INTO query_log (question, category, campus, answer_type, response_ms, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (db.mask(question)[:200], category, campus, result["answer_type"], result["elapsed_ms"], db.now()))
    return result


def add_faq(pending_id: int, question: str, answer: str, category: str, campus: str | None) -> int:
    """학과 조교 답변을 FAQ로 저장하고 바로 검색에 쓰이게 한다 (FR-029, PER-010). 승인 단계 없음."""
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
