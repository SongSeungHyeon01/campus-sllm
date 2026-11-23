"""Q&A 바탕 질문 50개를 실행 중인 서버에 보내고, 나간 답과 근거를 관리 웹 '평가 결과'에 남긴다.

사용 (ask-campus 폴더에서)
  .venv/Scripts/python scripts/eval_qna.py run dev  "1차"          # dev 30개
  .venv/Scripts/python scripts/eval_qna.py run test "최종"         # test 20개 (마지막에 한 번만)
  .venv/Scripts/python scripts/eval_qna.py judge "1차" 판정.json    # {"Q01": ["맞음", "이유"], …}
채점은 단어 포함이 아니라 정답 요지(key)와 답을 읽고 비교한다: 맞음 / 부분 / 틀림.
바탕이 된 Q&A 글은 서버에 exclude로 보내 검색에서 뺀다.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from eval_live import post  # noqa: E402
from src.server import db  # noqa: E402


def run(split: str, name: str, keep_src: bool = False):
    """split이 new면 questions_qna20, 그 밖은 questions_qna50. keep_src면 바탕 글을 빼지 않는다 (실제 서비스 조건)."""
    f = "questions_qna20.jsonl" if split == "new" else "questions_qna50.jsonl"
    items = [json.loads(l) for l in (ROOT / "eval" / f).open(encoding="utf-8")]
    items = [x for x in items if split in ("all", x["split"])]
    for x in items:
        r = post("/api/v1/ask", {"question": x["q"], "campus": x["campus"], "test": True,
                                 "exclude": [f"articleNo={x['src']}"] if x["src"] and not keep_src else []})
        with db.connect() as con:
            log = con.execute("SELECT answer, contexts FROM query_log WHERE log_id = ?", (r["log_id"],)).fetchone()
            con.execute("DELETE FROM eval_result WHERE run = ? AND qid = ?", (name, x["id"]))
            con.execute("INSERT INTO eval_result (run, qid, split, topic, who, campus, question, kind, key, src, answer_type, "
                        "answer, contexts, sources, response_ms, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (name, x["id"], x["split"], x["topic"], x["who"], x["campus"], x["q"], x["kind"], x["key"],
                         str(x["src"] or ""), r["answer_type"], log["answer"], log["contexts"],
                         json.dumps([s.get("label") or s.get("title") for s in r.get("sources") or []], ensure_ascii=False),
                         r["elapsed_ms"], db.now()))
        print(f"{x['id']} [{x['kind']}] {x['q']}\n   기준: {x['key']}\n   {r['answer_type']}: {r['answer'].replace(chr(10), ' / ')[:330]}")


def judge(name: str, path: str):
    v = json.load(open(path, encoding="utf-8"))
    with db.connect() as con:
        for qid, (verdict, reason) in v.items():
            assert verdict in ("맞음", "부분", "틀림"), qid
            con.execute("UPDATE eval_result SET verdict = ?, reason = ? WHERE run = ? AND qid = ?", (verdict, reason, name, qid))
        print(Counter(r[0] for r in con.execute("SELECT verdict FROM eval_result WHERE run = ?", (name,))))


if __name__ == "__main__":
    db.init()
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], "--keep-src" in sys.argv)
    else:
        judge(*sys.argv[2:4])
