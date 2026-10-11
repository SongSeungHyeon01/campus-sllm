"""SQLite 저장소. DB 모델링 v1.0의 테이블 중 MVP에 필요한 것만 만든다.

chunk, pending_question, faq, query_log (컬럼 이름은 DB 모델링과 같음)
pending_question·faq의 vec 열은 질문 임베딩(float32)이다. 이 두 표는 작아서 벡터 DB 대신 SQLite에 두고
numpy로 유사도를 계산한다 (Chroma는 빈 컬렉션에 처음 넣은 직후 검색하면 오류가 나는 문제가 있었음).
"""
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import config

KST = timezone(timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunk (
    chunk_id     VARCHAR(64) PRIMARY KEY,
    category     VARCHAR(20) NOT NULL,
    campus       VARCHAR(10),
    title        VARCHAR(300) NOT NULL,
    content      TEXT NOT NULL,
    source_url   VARCHAR(500),
    menu_path    VARCHAR(200),
    posted_at    DATETIME,
    collected_at DATETIME NOT NULL,
    indexed_at   DATETIME
);
CREATE TABLE IF NOT EXISTS pending_question (
    pending_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    question       VARCHAR(200) NOT NULL,
    category       VARCHAR(20),
    campus         VARCHAR(10),
    question_count INTEGER NOT NULL DEFAULT 1,
    status         VARCHAR(10) NOT NULL DEFAULT '대기',
    first_asked_at DATETIME NOT NULL,
    last_asked_at  DATETIME NOT NULL,
    expires_at     DATETIME NOT NULL,
    handled_at     DATETIME,
    vec            BLOB
);
CREATE TABLE IF NOT EXISTS faq (
    faq_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    pending_id INTEGER UNIQUE REFERENCES pending_question(pending_id),
    question   VARCHAR(100) NOT NULL,
    answer     TEXT NOT NULL,
    category   VARCHAR(20) NOT NULL,
    campus     VARCHAR(10),
    ask_count  INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    indexed_at DATETIME,
    vec        BLOB
);
CREATE TABLE IF NOT EXISTS query_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    question    VARCHAR(200) NOT NULL,
    category    VARCHAR(20),
    campus      VARCHAR(10),
    answer_type VARCHAR(10) NOT NULL,
    response_ms INTEGER NOT NULL,
    created_at  DATETIME NOT NULL
);
"""

_PHONE = re.compile(r"01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}")
_STUDENT_NO = re.compile(r"(?<!\d)\d{8,10}(?!\d)")


def now() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def mask(text: str) -> str:
    """질문을 저장하기 전에 전화번호·학번 형태를 가린다 (2.6, FR-028)."""
    return _STUDENT_NO.sub("***", _PHONE.sub("***", text)).strip()


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with connect() as con:
        con.executescript(SCHEMA)
        # 이전에 만든 DB에는 vec 열이 없으므로 추가한다
        for table in ("pending_question", "faq"):
            cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
            if "vec" not in cols:
                con.execute(f"ALTER TABLE {table} ADD COLUMN vec BLOB")


def expires_from(ts: str) -> str:
    return (datetime.fromisoformat(ts) + timedelta(days=config.PENDING_DAYS)).isoformat(timespec="seconds")
