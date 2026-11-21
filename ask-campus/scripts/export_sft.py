"""관리 웹에서 고친 답(답변 피드백)을 파인튜닝(SFT) 학습 데이터로 내보낸다.

사용 (ask-campus 폴더에서): .venv/Scripts/python scripts/export_sft.py   → data/sft/train.jsonl

- sLLM이 답했던 피드백만 쓴다. 시간표 계산·FAQ·되묻기 답은 모델이 만든 답이 아니라서 학습할 거리가 없다.
- 한 줄 = 서버가 실제로 sLLM에 보낸 것과 같은 형식의 대화 하나:
  system(답변 규칙 + 그때 넘긴 근거) / user(학생 질문) / assistant(관리자가 고친 답)
  → 같은 근거를 받았을 때 고친 답처럼 답하도록 배운다.
- 학습은 예시가 수백 개 쌓인 뒤에 한다. 적으면 효과가 없고, 지금 잘하는 '모르면 모른다'가 망가질 수 있다.
- data/는 git에 올라가지 않는다. 질문은 저장할 때 이미 전화번호·학번 형태를 가렸다.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.server import db, llm  # noqa: E402
from src.server.rag import _now_text  # noqa: E402

OUT = ROOT / "data" / "sft" / "train.jsonl"
ENOUGH = 300          # 이 정도는 모여야 학습을 해 볼 만하다 (대략적인 기준)


def main():
    db.init()
    with db.connect() as con:
        rows = con.execute(
            "SELECT f.question, f.corrected_answer, f.created_at, q.contexts, q.created_at AS asked_at "
            "FROM answer_feedback f JOIN query_log q ON q.log_id = f.log_id "
            "WHERE f.status = '고침' AND f.corrected_answer IS NOT NULL").fetchall()
    out, skipped = [], 0
    for r in rows:
        ctx = json.loads(r["contexts"] or "{}")
        if ctx.get("by") != "llm" or not ctx.get("contexts"):
            skipped += 1
            continue
        today = _now_text(datetime.fromisoformat(r["asked_at"]))
        material = "\n\n".join(f"■ {c}" for c in ctx["contexts"])
        out.append({"messages": [
            {"role": "system", "content": llm.SYSTEM.format(today=today) + "\n\n[자료]\n" + material},
            {"role": "user", "content": r["question"]},
            {"role": "assistant", "content": r["corrected_answer"].strip()},
        ]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(f"학습 예시 {len(out)}개 → {OUT} (sLLM 답이 아니라 뺀 것 {skipped}개)")
    if len(out) < ENOUGH:
        print(f"아직 적습니다. {ENOUGH}개 정도 모인 뒤 학습하는 것을 권합니다.")


if __name__ == "__main__":
    main()
