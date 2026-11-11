"""sLLM 후보 모델을 같은 질문으로 비교한다 (서버를 끄고 실행, 모델 하나당 한 번).

사용 (ask-campus 폴더에서):
  set ASK_LLM_MODEL=kakaocorp/kanana-2-3b-instruct
  set ASK_LLM_QUANT=4bit
  .venv/Scripts/python scripts/model_compare.py 결과.json

- DB는 복사본을 쓰고 FAQ·답변 대기를 비운다 (FAQ가 먼저 걸려 sLLM을 건너뛰지 않게, 실제 DB는 건드리지 않게).
- 시각은 2026-11-10(화) 14:00으로 고정한다.
- 통학버스 시간표 질문은 코드가 답을 계산하므로 넣지 않았다 (time_test.py 참고).
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tmp_db = Path(tempfile.mkdtemp()) / "compare.db"
shutil.copy(ROOT / "data" / "askcampus.db", tmp_db)
with sqlite3.connect(tmp_db) as con:
    con.execute("DELETE FROM faq")
    con.execute("DELETE FROM pending_question")
os.environ["ASK_DB"] = str(tmp_db)

sys.path.insert(0, str(ROOT))
import torch  # noqa: E402
from src.server import config, db, llm, rag  # noqa: E402

# (분류, 질문, 캠퍼스, 기대)
#  answer: 기대 문자열 중 하나가 답에 있어야 통과
#  none:   근거없음이어야 통과 (자료에 없음)
#  trap:   자료에 일부만 있음 → 근거없음이거나, 없는 정보를 지어내지 않아야 함 (사람이 확인)
CASES = [
    ("answer", "2학기 기말고사 언제야?", "아산", ["12.08", "12월 8일", "12월 08일", "12. 08"]),
    ("answer", "2학기 성적 확인 및 정정 기간 알려줘", "아산", ["12.23", "12월 23일", "12. 23"]),
    ("answer", "내년 1학기 수강신청 언제 해?", "아산", ["02.15", "2월 15일", "02. 15"]),
    ("answer", "등록금 환불 2/3선 언제야?", "아산", ["10.30", "10월 30일", "10. 30"]),
    ("answer", "2학기 개강일이 언제였어?", "아산", ["09.01", "9월 1일", "09. 01", "9월 01일"]),
    ("answer", "폐강된 과목 수강정정은 언제 해야 돼?", "아산", ["09. 10", "9월 10일", "09.10", "9. 10"]),
    ("answer", "학습법 공모전 총 상금 얼마야?", "아산", ["190만", "30만"]),   # 모집 공고(대상 30만 …)와 결과 공고(총 190만) 둘 다 있음
    ("answer", "학습법 공모전 대상 상금은 얼마야?", "아산", ["30만"]),
    ("answer", "안전교육 영상 공모전 상금 얼마야?", "아산", ["800만"]),
    ("answer", "국악 동아리 있어?", "영동", ["한맥"]),
    ("answer", "수강정정 언제까지야?", "아산", None),          # 공지가 여러 개라 기대값 없이 내용 확인
    ("answer", "2학기 일반휴학 신청 기간 알려줘", "아산", None),
    ("none", "편입생 전공 학점 인정 몇 학점까지야?", "아산", None),
    ("none", "기숙사 신청 언제 해?", "아산", None),
    ("none", "학식 메뉴 알려줘", "아산", None),
    ("none", "도서관 몇 시에 닫아?", "아산", None),
    ("trap", "2학기 기말고사 시험 장소 어디야?", "아산", None),
    ("trap", "국악 동아리 한맥 연락처 알려줘", "영동", None),        # 자료의 연락처 칸이 '010-'로 비어 있음 → 번호를 지어내면 안 됨
    ("trap", "한맥 동아리 회비 얼마야?", "영동", None),
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "compare.json"
    now = datetime(2026, 11, 10, 14, 0, tzinfo=db.KST)
    rag._now = lambda: now

    calls = []                       # sLLM이 실제로 불렸는지, 생성 시간
    orig = llm.answer

    def timed(*a, **k):
        t = time.perf_counter()
        r = orig(*a, **k)
        calls.append((time.perf_counter() - t, r))
        return r
    llm.answer = timed

    t = time.perf_counter()
    llm.warm_up()
    load_s = time.perf_counter() - t
    calls.clear()
    torch.cuda.reset_peak_memory_stats()

    rows, score = [], {"answer": [0, 0], "none": [0, 0]}
    for kind, q, campus, expect in CASES:
        n = len(calls)
        r = rag.ask(q, None, campus)
        used_llm = len(calls) > n
        raw = calls[-1][1] if used_llm else None
        ans = r["answer"]
        if kind == "answer":
            ok = r["answer_type"] == "문서" and (expect is None or any(e in ans for e in expect))
        elif kind == "none":
            ok = r["answer_type"] == "근거없음"
        else:
            ok = None
        if ok is not None:
            score[kind][0] += ok
            score[kind][1] += 1
        rows.append({"kind": kind, "q": q, "type": r["answer_type"], "ok": ok, "ms": r["elapsed_ms"],
                     "llm": used_llm, "answer": ans, "raw": raw})
        mark = {True: "PASS", False: "FAIL", None: "CHECK"}[ok]
        print(f"{mark:5} [{kind}] {q} → {r['answer_type']} {r['elapsed_ms']}ms llm={used_llm}")
        print("      " + ans.replace("\n", " / ")[:200])

    gen = [c[0] for c in calls]
    summary = {
        "model": config.LLM_MODEL, "quant": config.LLM_QUANT or "bf16",
        "load_s": round(load_s, 1),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
        "answer_pass": score["answer"], "none_pass": score["none"],
        "llm_calls": len(gen),
        "gen_avg_s": round(sum(gen) / len(gen), 2) if gen else None,
        "gen_max_s": round(max(gen), 2) if gen else None,
    }
    print(json.dumps(summary, ensure_ascii=False))
    Path(out).write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
