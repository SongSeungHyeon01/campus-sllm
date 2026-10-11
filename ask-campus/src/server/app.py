"""물어봐 캠퍼스 MVP 서버 (API 명세서 v1.0의 일부).

앱 API:   GET /api/v1/health, POST /api/v1/ask, GET /api/v1/faqs/{faq_id}
관리 웹:  /admin (임시 비밀번호 로그인) → 답변 대기 → 답변 작성 → FAQ 즉시 반영

실행 (ask-campus 폴더에서):
  set ASK_ADMIN_PASSWORD=원하는비밀번호
  .venv/Scripts/python -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000
"""
import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import config, db, index, llm, rag

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
COOKIE = "askcampus_admin"
CATEGORIES = ["학사정보", "통학버스", "동아리·행사", "교외활동", "일반공지"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    index.embedder()                       # 임베딩 모델 미리 올림
    if config.USE_LLM:
        llm.warm_up()                      # sLLM 미리 올림 (첫 질문 지연 방지)
    yield


app = FastAPI(title="물어봐 캠퍼스 MVP", lifespan=lifespan)


# ---------------------------------------------------------------- 앱 API
class AskIn(BaseModel):
    question: str = Field(..., description="질문 (1~200자)")
    category: str | None = None
    campus: str | None = None
    interests: list[str] = []


def error(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


_rate: dict[str, list[float]] = {}


def rate_limited(key: str, per_minute: int = 20) -> bool:
    """접속 주소별 분당 요청 수 (메모리에서만 세고 저장하지 않음, 2.6)."""
    now = time.monotonic()
    hits = [t for t in _rate.get(key, []) if now - t < 60]
    hits.append(now)
    _rate[key] = hits
    return len(hits) > per_minute


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
    if rate_limited(request.client.host if request.client else "?"):
        return error(429, "RATE_LIMITED", "잠시 후 다시 질문해 주세요.")
    return rag.ask(q, body.category, body.campus)


@app.get("/api/v1/faqs/{faq_id}")
def faq_detail(faq_id: int):
    with db.connect() as con:
        r = con.execute("SELECT * FROM faq WHERE faq_id = ?", (faq_id,)).fetchone()
    if not r:
        return error(404, "NOT_FOUND", "FAQ를 찾을 수 없습니다.")
    return {"faq_id": r["faq_id"], "question": r["question"], "answer": r["answer"], "category": r["category"],
            "source_label": f"학과 조교 답변 · {r['created_at'][:10]}"}


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
def login(password: str = Form(...)):
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
    return TEMPLATES.TemplateResponse(request, "pending.html", {"rows": rows, "stats": stats, "menu": "pending"})


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


@app.get("/admin/faqs", response_class=HTMLResponse)
def faq_list(request: Request, done: int = 0):
    need_login(request)
    with db.connect() as con:
        rows = con.execute("SELECT * FROM faq ORDER BY created_at DESC").fetchall()
    return TEMPLATES.TemplateResponse(request, "faqs.html", {"rows": rows, "done": done, "menu": "faqs"})
