"""학습 데이터 후보를 만든다 (관리 웹 '학습 데이터'에서 사람이 확인·승인한 것만 학습에 쓴다).

사용 (ask-campus 폴더에서, 서버를 켜고): .venv/Scripts/python scripts/make_sft_pool.py
1) 앞으로 채점에 쓸 Q&A 글 30개를 떼어 놓는다 (eval/holdout_qna.json, 글 번호만). 질문도 근거도 학습에 넣지 않는다.
2) 나머지 실제 학생 질문을 서버에 물어 그때의 근거와 답 초안을 모은다 (평가 표시로 보내 답변 대기에 섞이지 않음).
3) 질문 기록에서 sLLM이 답한 질문도 후보로 넣는다. 기존 108문항·페르소나 18문항(회귀 평가)은 뺀다.
다시 실행하면 새 질문만 더한다. 이미 확인한 것은 바뀌지 않는다.
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from eval_live import post  # noqa: E402
from src.server import db, rag  # noqa: E402
from src.server.build_index import _PERSONAL  # noqa: E402

HOLD = ROOT / "eval" / "holdout_qna.json"


def no(url: str) -> str:
    return re.search(r"articleNo=(\d+)", url)[1]


def load_posts():
    g, meta = defaultdict(list), {}
    for line in (ROOT / "data" / "chunks_login.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r["category"] == "Q&A":
            g[r["source_url"]].append(r["content"])
            meta[r["source_url"]] = (r["metadata"].get("posted_at") or "", r["title"][5:])
    out = {}
    for u, cs in g.items():
        c = "\n".join(cs)
        m = re.search(r"질문:\s*(.*?)(?:학교 답변:|$)", c, re.S)
        out[u] = {"date": meta[u][0], "title": meta[u][1], "q": re.sub(r"\s+", " ", m[1]).strip() if m else "",
                  "a": re.sub(r"\s+", " ", c.split("학교 답변:", 1)[1]).strip() if "학교 답변:" in c else "", "chunks": cs}
    return out


def reserve(posts) -> set[str]:
    if HOLD.exists():
        return set(json.loads(HOLD.read_text(encoding="utf-8")))
    # 11/22 새 질문 20개를 만들 때 읽은 38개(같은 시드의 앞부분) 뒤에서 고른다. 아직 아무도 시험에 쓰지 않은 글
    us = sorted(u for u, p in posts.items() if p["date"] < "2023" and p["a"] and "유선" not in "".join(p["chunks"]))
    random.Random(2211).shuffle(us)
    hold = sorted(no(u) for u in us[38:68])
    HOLD.write_text(json.dumps(hold), encoding="utf-8")
    return set(hold)


def clean_draft(answer: str) -> str:
    """서버가 덧붙인 안내를 떼고 모델이 쓴 부분만 남긴다."""
    lines = [ln for ln in answer.split("\n") if not ln.startswith(("학교 Q&A의 지난 답변(", "올해 일정은 아직 올라오지", "· 이 내용은 "))]
    text = "\n".join(lines).strip()
    return rag.llm.NOT_FOUND if text.startswith(rag.llm.NOT_FOUND) else text


def main():
    db.init()
    posts = load_posts()
    hold = reserve(posts)
    hold_text = [c for u, p in posts.items() if no(u) in hold for c in p["chunks"]]
    reg = {json.loads(x)["q"] for f in ("questions.jsonl", "questions_persona.jsonl")
           for x in (ROOT / "eval" / f).open(encoding="utf-8") if x.strip()}
    reg |= {rag._normalize(q) for q in reg}
    added = Counter()

    def add(q, campus, ctx, answer, source, ref, hint, asked):
        if not ctx or q in reg or any(h in c for c in ctx for h in hold_text):
            added["뺌"] += 1
            return
        with db.connect() as con:
            cur = con.execute("INSERT OR IGNORE INTO sft_example (question, campus, contexts, draft, answer, source, ref, hint, "
                              "asked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (q, campus, json.dumps(ctx, ensure_ascii=False), clean_draft(answer), clean_draft(answer),
                               source, ref, hint, asked))
            added[source] += cur.rowcount

    def from_log(where: str, args: tuple):
        with db.connect() as con:
            return con.execute("SELECT question, campus, contexts, answer, created_at FROM query_log WHERE " + where
                               + " ORDER BY log_id DESC", args).fetchall()

    todo = [(u, p) for u, p in posts.items() if no(u) not in hold and 8 <= len(p["q"]) <= 200]
    with db.connect() as con:
        done = {r[0] for r in con.execute("SELECT src FROM sft_asked")}
    for i, (u, p) in enumerate(todo, 1):
        if no(u) in done:
            continue
        r = post("/api/v1/ask", {"question": p["q"], "campus": "영동" if "영동" in p["q"] else "아산", "test": True,
                                 "exclude": [f"articleNo={n}" for n in sorted(hold)]})
        row = from_log("log_id = ?", (r["log_id"],))[0]
        d = json.loads(row["contexts"] or "{}")
        if d.get("by") == "llm":
            hint = "학교도 개인 상황을 확인해 답한 질문입니다. '모른다'가 맞을 수 있습니다." if _PERSONAL.search(p["a"]) else ""
            add(row["question"], row["campus"], d["contexts"], row["answer"], "학생 Q&A", f"{p['date']} 학교 답변: {p['a'][:600]}",
                hint, row["created_at"])
        with db.connect() as con:
            con.execute("INSERT OR IGNORE INTO sft_asked (src) VALUES (?)", (no(u),))
        if i % 20 == 0:
            print(f"{i}/{len(todo)}", flush=True)
    keys = {}
    for f in ("questions_qna50.jsonl", "questions_qna20.jsonl"):
        for x in map(json.loads, (ROOT / "eval" / f).open(encoding="utf-8")):
            keys[rag._normalize(x["q"])] = x["key"]
    for row in from_log("contexts LIKE '%\"by\": \"llm\"%'", ()):
        d = json.loads(row["contexts"])
        ref = keys.get(row["question"])
        add(row["question"], row["campus"], d["contexts"], row["answer"], "질문 기록", f"평가 때 적은 정답 기준: {ref}" if ref else "",
            "", row["created_at"])
    print(dict(added))


if __name__ == "__main__":
    main()
