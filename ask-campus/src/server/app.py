"""물어봐 캠퍼스 MVP 서버 (API 명세서 v1.0의 일부).

앱 API:   GET /api/v1/health, POST /api/v1/ask, GET /api/v1/faqs/{faq_id}
관리 웹:  /admin (임시 비밀번호 로그인) → 답변 대기 → 답변 작성 → FAQ 즉시 반영

실행 (ask-campus 폴더에서):
  set ASK_ADMIN_PASSWORD=원하는비밀번호
  .venv/Scripts/python -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000
"""
import hashlib
import json
import hmac
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import config, db, external, index, llm, rag

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
COOKIE = "askcampus_admin"
CATEGORIES = ["학사정보", "통학버스", "동아리·행사", "교외활동", "일반공지"]


REINDEX_TOKEN_FILE = config.DATA / ".reindex_token"   # 자동 수집 스크립트(scripts/refresh.py)만 읽는 일회용 토큰


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    index.embedder()                       # 임베딩 모델 미리 올림
    if config.USE_LLM:
        llm.warm_up()                      # sLLM 미리 올림 (첫 질문 지연 방지)
    REINDEX_TOKEN_FILE.write_text(secrets.token_hex(24), encoding="utf-8")
    # 외부 공모전 목록을 미리 읽어 둔다 (첫 공모전 질문이 사이트 9쪽을 기다리지 않게). 실패해도 서버는 뜬다
    import threading
    from datetime import datetime
    threading.Thread(target=lambda: external.site_contests(datetime.now(db.KST)), daemon=True).start()
    yield


app = FastAPI(title="물어봐 캠퍼스 MVP", lifespan=lifespan)
_reindex_lock = threading.Lock()


@app.post("/internal/reindex", include_in_schema=False)
def reindex(request: Request):
    """자동 수집 뒤 서버 안에서 색인을 다시 만든다 (Chroma를 두 프로세스가 같이 쓰지 않게).

    이 PC에서 직접 온 요청만 받는다: 주소가 127.0.0.1이고, Cloudflare 터널을 거친 표시(CF-Connecting-IP)가 없고,
    서버가 켜질 때 data/에 만든 토큰이 맞아야 한다. 외부에서는 터널을 거쳐도 열리지 않는다.
    """
    host = request.client.host if request.client else ""
    expected = REINDEX_TOKEN_FILE.read_text(encoding="utf-8") if REINDEX_TOKEN_FILE.exists() else ""
    if (host not in ("127.0.0.1", "::1") or "cf-connecting-ip" in request.headers
            or not expected or not hmac.compare_digest(request.headers.get("x-reindex-token", ""), expected)):
        return error(403, "FORBIDDEN", "허용되지 않은 요청입니다.")
    if not _reindex_lock.acquire(blocking=False):
        return error(409, "BUSY", "이미 색인을 만드는 중입니다.")
    try:
        from . import build_index
        return {"chunks": build_index.main()}
    finally:
        _reindex_lock.release()


# ---------------------------------------------------------------- 앱 API
class AskIn(BaseModel):
    question: str = Field(..., description="질문 (1~200자)")
    category: str | None = None
    test: bool = Field(False, description="평가 스크립트용. 이 PC에서 보낸 요청만 인정")
    exclude: list[str] = Field(default_factory=list, description="평가 때 검색에서 뺄 글 주소의 끝부분")
    campus: str | None = None
    interests: list[str] = []
    department: str | None = Field(None, description="학과 (되묻기에서 고른 값). 저장하지 않고 이번 답에만 쓴다")


def error(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


_rate: dict[str, list[float]] = {}


def client_ip(request: Request) -> str:
    """요청한 사람의 주소. Cloudflare Tunnel을 거치면 모든 요청이 이 PC(127.0.0.1)에서 온 것처럼 보이므로,
    이 PC에서 들어온 요청일 때만 Cloudflare가 붙인 CF-Connecting-IP를 믿는다 (외부에서 이 헤더를 꾸며 보내도 무시됨)."""
    host = request.client.host if request.client else "?"
    if host in ("127.0.0.1", "::1"):
        return request.headers.get("cf-connecting-ip", host)
    return host


def rate_limited(key: str, per_minute: int = 20) -> bool:
    """접속 주소별 분당 요청 수 (메모리에서만 세고 저장하지 않음, 2.6)."""
    now = time.monotonic()
    hits = [t for t in _rate.get(key, []) if now - t < 60]
    hits.append(now)
    _rate[key] = hits
    return len(hits) > per_minute


@app.get("/", response_class=HTMLResponse)
def chat_page(request: Request):
    """시험용 웹 채팅 화면 (앱과 같은 /api/v1/ask 사용)."""
    return TEMPLATES.TemplateResponse(request, "chat.html")


@app.get("/api/v1/health")
def health():
    with db.connect() as con:
        row = con.execute("SELECT MAX(collected_at) AS t FROM chunk").fetchone()
    return {"status": "ok", "model_ready": (not config.USE_LLM) or llm.ready(), "data_updated_at": row["t"]}


@app.post("/api/v1/ask")
def ask(body: AskIn, request: Request):
    q = (body.question or "").strip()
    if not 1 <= len(q) <= 200:
        return error(400, "INVALID_QUESTION", "질문은 1~200자로 입력해 주세요.")
    if rate_limited(client_ip(request)):
        return error(429, "RATE_LIMITED", "잠시 후 다시 질문해 주세요.")
    # 평가 표시는 이 PC에서 직접 보낸 요청만 받는다 (터널로 들어온 요청은 항상 사용자 질문)
    host = request.client.host if request.client else ""
    test = body.test and host in ("127.0.0.1", "::1") and "cf-connecting-ip" not in request.headers
    return rag.ask(q, body.category, body.campus, body.department, test, tuple(body.exclude[:60]))


class FeedbackIn(BaseModel):
    log_id: int
    comment: str = Field("", description="무엇이 틀렸는지 (선택, 300자까지)")


@app.post("/api/v1/feedback")
def feedback(body: FeedbackIn, request: Request):
    """채팅의 '답이 이상해요'. 그 답의 질문·답·답변 유형을 질문 기록에서 복사해 피드백으로 남긴다 (같은 답은 한 번만)."""
    if rate_limited(client_ip(request)):
        return error(429, "RATE_LIMITED", "잠시 후 다시 시도해 주세요.")
    with db.connect() as con:
        log = con.execute("SELECT * FROM query_log WHERE log_id = ?", (body.log_id,)).fetchone()
        if log is None:
            return error(404, "NOT_FOUND", "답변 기록을 찾을 수 없습니다.")
        if con.execute("SELECT 1 FROM answer_feedback WHERE log_id = ?", (body.log_id,)).fetchone() is None:
            con.execute("INSERT INTO answer_feedback (log_id, question, campus, answer_type, answer, comment, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (log["log_id"], log["question"], log["campus"], log["answer_type"], log["answer"],
                         db.mask(body.comment.strip())[:300], db.now()))
    return {"ok": True}


@app.get("/api/v1/faqs/{faq_id}")
def faq_detail(faq_id: int):
    with db.connect() as con:
        r = con.execute("SELECT * FROM faq WHERE faq_id = ?", (faq_id,)).fetchone()
    if not r:
        return error(404, "NOT_FOUND", "FAQ를 찾을 수 없습니다.")
    return {"faq_id": r["faq_id"], "question": r["question"], "answer": r["answer"], "category": r["category"],
            "source_label": f"관리자 등록 답변 · {r['created_at'][:10]}"}


# ---------------------------------------------------------------- 관리 웹 (임시 로그인)
def _token() -> str:
    return hmac.new(config.SECRET.encode(), b"admin", hashlib.sha256).hexdigest()


def logged_in(request: Request) -> bool:
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), _token())


def need_login(request: Request):
    if not logged_in(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return TEMPLATES.TemplateResponse(request, "login.html", {"error": error,
                                                              "no_password": not config.ADMIN_PASSWORD})


@app.post("/admin/login")
def login(request: Request, password: str = Form(...)):
    # 비밀번호를 계속 넣어 보는 것을 막는다: 같은 주소에서 1분에 5번까지 (터널로 외부에 열려 있어서)
    if rate_limited("login:" + client_ip(request), per_minute=5):
        return RedirectResponse("/admin/login?error=1", status_code=303)
    if not config.ADMIN_PASSWORD or not hmac.compare_digest(password, config.ADMIN_PASSWORD):
        return RedirectResponse("/admin/login?error=1", status_code=303)
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie(COOKIE, _token(), httponly=True, samesite="lax", max_age=12 * 3600)
    return resp


@app.post("/admin/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/admin", response_class=HTMLResponse)
def pending_list(request: Request):
    need_login(request)
    with db.connect() as con:
        rows = con.execute("SELECT * FROM pending_question WHERE status = '대기' "
                           "ORDER BY question_count DESC, first_asked_at").fetchall()
        stats = con.execute("SELECT COUNT(*) AS n, AVG(response_ms) AS ms FROM query_log "
                            "WHERE substr(created_at, 1, 10) = substr(?, 1, 10)", (db.now(),)).fetchone()
        # 그때 나간 답: 같은 질문의 가장 최근 기록 (비슷해서 묶인 질문은 문장이 달라 없을 수 있음)
        last = {r["pending_id"]: con.execute(
            "SELECT answer_type, answer, created_at FROM query_log WHERE question = ? ORDER BY log_id DESC LIMIT 1",
            (r["question"],)).fetchone() for r in rows}
    return TEMPLATES.TemplateResponse(request, "pending.html", {"rows": rows, "stats": stats, "last": last,
                                                                "menu": "pending"})


SFT_GOAL = 300


@app.get("/admin/sft", response_class=HTMLResponse)
def sft_page(request: Request, status: str = "대기", after: int = 0, advice: str = ""):
    """학습 데이터: 한 번에 하나씩 질문·근거·답 초안을 보고 고쳐 승인한다. advice로 추천별로 나눠 본다."""
    need_login(request)
    with db.connect() as con:
        counts = {r[0]: r[1] for r in con.execute("SELECT status, COUNT(*) FROM sft_example GROUP BY status")}
        unknown = con.execute("SELECT COUNT(*) FROM sft_example WHERE status = '승인' AND answer = ?", (llm.NOT_FOUND,)).fetchone()[0]
        kinds = {r[0]: r[1] for r in con.execute(
            "SELECT COALESCE(advice, ''), COUNT(*) FROM sft_example WHERE status = '대기' GROUP BY 1")}
        r = con.execute("SELECT * FROM sft_example WHERE status = '대기' AND sft_id > ? AND (? = '' OR advice = ?) "
                        "ORDER BY sft_id LIMIT 1", (after, advice, advice)).fetchone()
        drops = con.execute("SELECT sft_id, question, advice_note FROM sft_example WHERE status = '대기' AND advice = '제외' "
                            "ORDER BY sft_id").fetchall() if status == "대기" and advice == "제외" else []
        rows = [] if status == "대기" else con.execute(
            "SELECT * FROM sft_example WHERE status = ? ORDER BY handled_at DESC LIMIT 300", (status,)).fetchall()
    return TEMPLATES.TemplateResponse(request, "sft.html", {
        "r": r, "ctx": json.loads(r["contexts"]) if r else [], "rows": rows, "counts": counts, "status": status,
        "after": after, "advice": advice, "kinds": kinds, "drops": drops, "goal": SFT_GOAL, "unknown": unknown, "menu": "sft"})


@app.post("/admin/sft/drop")
def sft_drop(request: Request, ids: list[int] = Form([])):
    """'제외 추천' 목록에서 체크한 것만 한꺼번에 제외한다."""
    need_login(request)
    with db.connect() as con:
        con.executemany("UPDATE sft_example SET status = '제외', handled_at = ? WHERE sft_id = ? AND status = '대기' AND advice = '제외'",
                        [(db.now(), i) for i in ids])
    return RedirectResponse("/admin/sft", status_code=303)


@app.post("/admin/sft/{sid}")
def sft_save(request: Request, sid: int, action: str = Form(...), answer: str = Form(""), advice: str = Form("")):
    need_login(request)
    more = f"&advice={quote(advice)}" if advice else ""
    answer = answer.replace("\r\n", "\n").strip()
    if action not in ("approve", "unknown", "dismiss", "undo") or (action == "approve" and not answer):
        return RedirectResponse(f"/admin/sft?after={max(0, sid - 1)}{more}", status_code=303)
    with db.connect() as con:
        if action == "undo":
            con.execute("UPDATE sft_example SET status = '대기', handled_at = NULL WHERE sft_id = ?", (sid,))
        elif action == "dismiss":
            con.execute("UPDATE sft_example SET status = '제외', handled_at = ? WHERE sft_id = ? AND status = '대기'", (db.now(), sid))
        else:
            con.execute("UPDATE sft_example SET status = '승인', answer = ?, handled_at = ? WHERE sft_id = ? AND status = '대기'",
                        (llm.NOT_FOUND if action == "unknown" else answer[:600], db.now(), sid))
    return RedirectResponse("/admin/sft" if action == "undo" else f"/admin/sft?after={sid}{more}", status_code=303)


@app.get("/admin/candidates", response_class=HTMLResponse)
def candidates(request: Request, status: str = "대기"):
    """FAQ 후보: 초안을 관리자가 확인해 승인해야 학생 답변에 쓰인다."""
    need_login(request)
    with db.connect() as con:
        path = config.ROOT / "eval" / "faq_candidates.json"
        for x in json.loads(path.read_text(encoding="utf-8")) if path.exists() else []:
            con.execute("INSERT OR IGNORE INTO faq_candidate (question, answer, basis, todo) VALUES (?, ?, ?, ?)",
                        (x["q"], x["a"], x["basis"], x["check"]))
        rows = con.execute("SELECT * FROM faq_candidate WHERE status = ? ORDER BY cand_id", (status,)).fetchall()
        counts = {r[0]: r[1] for r in con.execute("SELECT status, COUNT(*) FROM faq_candidate GROUP BY status")}
    return TEMPLATES.TemplateResponse(request, "candidates.html", {"rows": rows, "counts": counts, "status": status,
                                                                   "menu": "candidates"})


@app.post("/admin/candidates/{cid}")
def candidate_save(request: Request, cid: int, action: str = Form(...), question: str = Form(...), answer: str = Form("")):
    need_login(request)
    question, answer = question.strip()[:100], answer.strip()
    with db.connect() as con:
        row = con.execute("SELECT status FROM faq_candidate WHERE cand_id = ?", (cid,)).fetchone()
    if row is None or row["status"] != "대기" or action not in ("approve", "save", "dismiss"):
        return RedirectResponse("/admin/candidates", status_code=303)
    if action == "approve" and not (question and answer):
        return RedirectResponse("/admin/candidates", status_code=303)
    status = {"approve": "승인", "save": "대기", "dismiss": "제외"}[action]
    with db.connect() as con:        # 질문은 후보 파일과 맞춰 두려고 바꾸지 않고, 승인할 때 고친 질문으로 FAQ를 만든다
        con.execute("UPDATE faq_candidate SET answer = ?, status = ?, handled_at = ? WHERE cand_id = ?",
                    (answer, status, db.now(), cid))
    if action == "approve":
        pid = rag.register_pending(question, "학사정보", None, index.embed([question])[0])
        rag.add_faq(pid, question, answer, "학사정보", None)
    return RedirectResponse("/admin/candidates", status_code=303)


VERDICTS = ("맞음", "부분", "틀림", "미채점")


@app.get("/admin/eval", response_class=HTMLResponse)
def eval_results(request: Request, run: str = "", verdict: str = ""):
    """평가 결과: 질문마다 나간 답, 모델이 본 근거, 정답 기준, 판정."""
    need_login(request)
    with db.connect() as con:
        runs = [r[0] for r in con.execute("SELECT run FROM eval_result GROUP BY run ORDER BY MAX(eval_id) DESC")]
        run = run if run in runs else (runs[0] if runs else "")
        rows = [dict(r) for r in con.execute("SELECT * FROM eval_result WHERE run = ? ORDER BY qid", (run,))]
    counts = {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS}
    rows = [r for r in rows if not verdict or r["verdict"] == verdict]
    for r in rows:
        r["ctx"] = json.loads(r["contexts"] or "{}").get("contexts", [])
        r["src_list"] = json.loads(r["sources"] or "[]")
    return TEMPLATES.TemplateResponse(request, "eval.html", {"rows": rows, "runs": runs, "run": run, "counts": counts,
                                                             "verdict": verdict, "verdicts": VERDICTS, "menu": "eval"})


@app.post("/admin/eval/{eid}")
def eval_verdict(request: Request, eid: int, verdict: str = Form(...)):
    need_login(request)
    if verdict not in VERDICTS:
        raise HTTPException(400)
    with db.connect() as con:
        row = con.execute("SELECT run FROM eval_result WHERE eval_id = ?", (eid,)).fetchone()
        con.execute("UPDATE eval_result SET verdict = ? WHERE eval_id = ?", (verdict, eid))
    return RedirectResponse("/admin/eval?run=" + quote(row["run"] if row else ""), status_code=303)


LOG_PAGE = 50


@app.get("/admin/logs", response_class=HTMLResponse)
def question_logs(request: Request, source: str = "user", kind: str = "", q: str = "", page: int = 1):
    """질문 기록: 어떤 질문에 어떤 답이 나갔는지."""
    need_login(request)
    source = source if source in ("user", "eval") else "user"
    page = min(max(1, page), 100000)
    cond, args = "source = ?", [source]
    if kind:
        cond, args = cond + " AND answer_type = ?", args + [kind]
    if q.strip():
        word = q.strip()[:50].lower()
        cond, args = cond + " AND (instr(lower(question), ?) OR instr(lower(answer), ?))", args + [word, word]
    with db.connect() as con:
        total = con.execute(f"SELECT COUNT(*) FROM query_log WHERE {cond}", args).fetchone()[0]
        rows = con.execute(f"SELECT log_id, question, campus, answer_type, answer, response_ms, created_at FROM query_log "
                           f"WHERE {cond} ORDER BY log_id DESC LIMIT ? OFFSET ?",
                           (*args, LOG_PAGE, (page - 1) * LOG_PAGE)).fetchall()
        kinds = [r[0] for r in con.execute("SELECT DISTINCT answer_type FROM query_log ORDER BY answer_type")]
        counts = {r[0]: r[1] for r in con.execute("SELECT source, COUNT(*) FROM query_log GROUP BY source")}
    return TEMPLATES.TemplateResponse(request, "logs.html", {
        "rows": rows, "total": total, "page": page, "pages": max(1, -(-total // LOG_PAGE)), "kinds": kinds,
        "counts": counts, "source": source, "kind": kind, "q": q, "menu": "logs"})


@app.get("/admin/pending/{pid}", response_class=HTMLResponse)
def answer_page(request: Request, pid: int):
    need_login(request)
    with db.connect() as con:
        row = con.execute("SELECT * FROM pending_question WHERE pending_id = ?", (pid,)).fetchone()
    if not row:
        raise HTTPException(404)
    return TEMPLATES.TemplateResponse(request, "answer.html", {"row": row, "categories": CATEGORIES,
                                                               "menu": "pending"})


@app.post("/admin/pending/{pid}/answer")
def answer_submit(request: Request, pid: int, question: str = Form(...), answer: str = Form(...),
                  category: str = Form(...), campus: str = Form("")):
    need_login(request)
    question, answer = question.strip()[:100], answer.strip()
    if not question or not answer:
        return RedirectResponse(f"/admin/pending/{pid}", status_code=303)
    with db.connect() as con:
        row = con.execute("SELECT status FROM pending_question WHERE pending_id = ?", (pid,)).fetchone()
    if not row or row["status"] != "대기":
        return RedirectResponse("/admin", status_code=303)
    rag.add_faq(pid, question, answer, category, campus or None)
    return RedirectResponse("/admin/faqs?done=1", status_code=303)


@app.post("/admin/pending/{pid}/not-mine")
def not_mine(request: Request, pid: int):
    need_login(request)
    rag.mark_not_mine(pid)
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/feedback", response_class=HTMLResponse)
def feedback_list(request: Request, status: str = "대기", done: int = 0):
    """학생이 '답이 이상해요'를 누른 답변 목록."""
    need_login(request)
    with db.connect() as con:
        rows = con.execute("SELECT * FROM answer_feedback WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        counts = {r["status"]: r["n"] for r in con.execute(
            "SELECT status, COUNT(*) AS n FROM answer_feedback GROUP BY status")}
    return TEMPLATES.TemplateResponse(request, "feedback.html", {"rows": rows, "counts": counts, "status": status,
                                                                 "done": done, "menu": "feedback"})


@app.get("/admin/feedback/{fid}", response_class=HTMLResponse)
def feedback_edit(request: Request, fid: int):
    need_login(request)
    with db.connect() as con:
        row = con.execute("SELECT * FROM answer_feedback WHERE feedback_id = ?", (fid,)).fetchone()
        log = con.execute("SELECT contexts FROM query_log WHERE log_id = ?", (row["log_id"],)).fetchone() if row else None
    if row is None:
        return RedirectResponse("/admin/feedback", status_code=303)
    ctx = json.loads(log["contexts"]) if log and log["contexts"] else {"by": None, "contexts": []}
    return TEMPLATES.TemplateResponse(request, "feedback_edit.html", {"row": row, "ctx": ctx, "categories": CATEGORIES,
                                                                      "menu": "feedback"})


@app.post("/admin/feedback/{fid}")
def feedback_save(request: Request, fid: int, corrected_answer: str = Form(...), add_faq: str = Form(""),
                  category: str = Form("학사정보")):
    """올바른 답을 저장한다. '사실 정보'면 FAQ에도 바로 넣어 같은 질문에 이 답을 쓰게 한다.
    저장한 답은 scripts/export_sft.py가 파인튜닝 데이터로 내보낸다 (sLLM이 답한 경우만)."""
    need_login(request)
    answer = corrected_answer.strip()
    if not answer:
        return RedirectResponse(f"/admin/feedback/{fid}", status_code=303)
    with db.connect() as con:
        row = con.execute("SELECT * FROM answer_feedback WHERE feedback_id = ?", (fid,)).fetchone()
        if row is None:
            return RedirectResponse("/admin/feedback", status_code=303)
        con.execute("UPDATE answer_feedback SET corrected_answer = ?, status = '고침', handled_at = ? WHERE feedback_id = ?",
                    (answer, db.now(), fid))
    if add_faq:
        qvec = index.embed([row["question"]])[0]
        pid = rag.register_pending(row["question"], category, row["campus"], qvec)
        rag.add_faq(pid, row["question"], answer, category, row["campus"])
    return RedirectResponse("/admin/feedback?done=1", status_code=303)


@app.post("/admin/feedback/{fid}/dismiss")
def feedback_dismiss(request: Request, fid: int):
    """답이 맞았거나 고칠 필요가 없는 피드백."""
    need_login(request)
    with db.connect() as con:
        con.execute("UPDATE answer_feedback SET status = '제외', handled_at = ? WHERE feedback_id = ?", (db.now(), fid))
    return RedirectResponse("/admin/feedback", status_code=303)


@app.get("/admin/faqs", response_class=HTMLResponse)
def faq_list(request: Request, done: int = 0):
    need_login(request)
    with db.connect() as con:
        rows = con.execute("SELECT * FROM faq ORDER BY created_at DESC").fetchall()
    return TEMPLATES.TemplateResponse(request, "faqs.html", {"rows": rows, "done": done, "menu": "faqs"})
