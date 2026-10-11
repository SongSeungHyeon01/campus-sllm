"""질문 하나를 처리한다 (API 명세 1-2 서버 처리 순서).

1) FAQ(학과 조교 답변)에서 거의 같은 질문을 찾으면 그 답변을 그대로 돌려줌
2) 아니면 청크를 검색해 기준 이상이면 sLLM이 근거만으로 답변
3) 근거가 없거나 sLLM이 "찾을 수 없습니다"라고 하면 답변 대기에 자동 등록 (FR-005, FR-028)

청크는 Chroma에서, FAQ·답변 대기는 SQLite vec 열에서 찾는다 (db.py 설명 참고).
"""
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
        if hits:
            top = hits[:config.CONTEXT_K]
            if config.USE_LLM:
                text = llm.answer(question, [h["document"] for h in top],
                                  datetime.now(db.KST).strftime("%Y년 %m월 %d일 (%a)"))
            else:
                text = top[0]["document"][:400]
            if text and not llm.is_not_found(text):
                result.update(answer_type="문서", answer=text, sources=_sources_from_chunks(top))
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
