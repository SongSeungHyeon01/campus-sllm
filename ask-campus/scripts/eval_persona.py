"""페르소나 평가 질문셋(eval/questions_persona.jsonl)을 돌려 말투별 정답률을 낸다 (서버를 끄고 실행).

사용 (ask-campus 폴더에서): .venv/Scripts/python scripts/eval_persona.py 결과.json

채점
- answer: 답변 유형이 '문서'이고 expect 중 하나가 답에 있음. expect_all이 있으면(두 질문) 묶음마다 하나씩 모두 있어야 함
- none: '근거없음'
- trap: 사람이 확인 (CHECK)
- 되묻기: 따로 센다 (CLARIFY). 질문이 정말 애매했는지는 사람이 본다
model_compare.py와 같은 조건: DB 복사본(FAQ·답변 대기 비움), 시각 2026-11-10(화) 14:00 고정.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tmp_db = Path(tempfile.mkdtemp()) / "persona.db"
shutil.copy(ROOT / "data" / "askcampus.db", tmp_db)
with sqlite3.connect(tmp_db) as con:
    con.execute("DELETE FROM faq")
    con.execute("DELETE FROM pending_question")
os.environ["ASK_DB"] = str(tmp_db)
sys.path.insert(0, str(ROOT))
from src.server import db, llm, rag  # noqa: E402


def passed(item: dict, r: dict) -> bool | None:
    ans, kind = r["answer"], item["kind"]
    if r["answer_type"] == "되묻기":
        return None
    if kind == "none":
        return r["answer_type"] == "근거없음"
    if kind != "answer":
        return None
    if r["answer_type"] != "문서":
        return False
    if item.get("expect_all"):
        return all(any(e in ans for e in grp) for grp in item["expect_all"])
    return not item.get("expect") or any(e in ans for e in item["expect"])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "persona.json"
    items = [json.loads(l) for l in (ROOT / "eval" / "questions_persona.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()]
    now = datetime(2026, 11, 10, 14, 0, tzinfo=db.KST)
    rag._now = lambda: now
    llm.warm_up()
    rows, by_style = [], defaultdict(lambda: [0, 0, 0])      # 맞음, 채점, 되묻기
    for it in items:
        r = rag.ask(it["q"], None, it.get("campus"))
        ok = passed(it, r)
        s = by_style[it["style"]]
        if r["answer_type"] == "되묻기":
            s[2] += 1
        elif ok is not None:
            s[0] += ok
            s[1] += 1
        mark = "CLARIFY" if r["answer_type"] == "되묻기" else {True: "PASS", False: "FAIL", None: "CHECK"}[ok]
        print(f"{mark:7} {it['id']} [{it['style']}] {it['q']} → {r['answer_type']}")
        print("        " + r["answer"].replace("\n", " / ")[:180])
        rows.append({**it, "type": r["answer_type"], "ok": ok, "answer": r["answer"], "ms": r["elapsed_ms"]})
    print("\n말투별 (맞음/채점, 되묻기)")
    for style, (o, n, c) in by_style.items():
        print(f"  {style:8} {o}/{n}" + (f", 되묻기 {c}" if c else ""))
    total = [sum(v[i] for v in by_style.values()) for i in range(3)]
    print(f"  전체     {total[0]}/{total[1]}, 되묻기 {total[2]}")
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
