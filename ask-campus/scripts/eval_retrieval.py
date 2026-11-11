"""검색 정확도 평가 (PER-003: 테스트 질문 80개 중 정답 근거가 상위 3개 안에 드는 비율 80% 이상).

sLLM을 쓰지 않고 임베딩·벡터 검색만 본다. 서버를 끄지 않아도 되지만 GPU 메모리가 빠듯하면 끄고 실행한다.

사용 (ask-campus 폴더에서):
  .venv/Scripts/python scripts/eval_retrieval.py                       # eval/questions.jsonl → eval/results/
  .venv/Scripts/python scripts/eval_retrieval.py --out eval/results/retrieval_리랭커전.json

질문 파일 형식 (eval/questions.jsonl, 한 줄에 질문 하나):
  kind   answer(자료에 답 있음) / none(자료에 없음) / trap(자료에 일부만 있음)
  gold   정답 근거 청크에 들어 있는 문자열 목록. 검색된 청크 본문에 하나라도 있으면 정답 근거로 본다.
  expect 답변에 들어가야 하는 문자열 (eval_e2e.py에서 사용)

출력:
  - 상위 1·3·5 정답률 (answer 질문), 분야별·말투별 상위 3 정답률
  - 근거 기준값(MIN_SCORE)별로: 답 있는 질문을 살리는 비율 / 없는 질문을 걸러 내는 비율
  - 상위 3에 못 든 질문 목록
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.server import config, index, rag  # noqa: E402

THRESHOLDS = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66]


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def check_gold_exists(items: list[dict]):
    """정답 문자열이 수집 자료에 실제로 있는지 먼저 확인 (오타나 재수집으로 사라진 경우를 잡음)."""
    chunks = [json.loads(l)["content"] for l in config.CHUNKS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    missing = [(it["id"], g) for it in items if it.get("gold") for g in it["gold"]
               if not any(g in c for c in chunks)]
    if missing:
        print("정답 문자열이 수집 자료에 없음 (질문셋 또는 자료 확인 필요):")
        for i, g in missing:
            print(f"  {i}: {g}")
        sys.exit(1)


def rank_of(hits: list[dict], gold: list[str]) -> int | None:
    for i, h in enumerate(hits):
        if any(g in h["document"] for g in gold):
            return i + 1
    return None


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({a / b * 100:.1f}%)" if b else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    items = load(Path(args.questions))
    check_gold_exists(items)

    vecs = index.embed([it["q"] for it in items])
    rows = []
    for it, v in zip(items, vecs):
        hits = index.search("chunks", v, config.TOP_K, rag._campus_filter(it.get("campus")))
        r = rank_of(hits, it["gold"]) if it.get("gold") else None
        rows.append({"id": it["id"], "kind": it["kind"], "domain": it["domain"], "style": it["style"],
                     "q": it["q"], "rank": r, "top_score": round(hits[0]["score"], 4) if hits else 0.0,
                     "gold_score": round(hits[r - 1]["score"], 4) if r else None,
                     "top3": [h["meta"].get("title") for h in hits[:3]]})

    ans = [r for r in rows if r["kind"] == "answer"]
    none = [r for r in rows if r["kind"] == "none"]
    n = len(ans)
    top = {k: sum(1 for r in ans if r["rank"] and r["rank"] <= k) for k in (1, 3, 5)}

    by = defaultdict(lambda: [0, 0])
    for r in ans:
        for key in (f"분야:{r['domain']}", f"말투:{r['style']}"):
            by[key][0] += bool(r["rank"] and r["rank"] <= 3)
            by[key][1] += 1

    # 기준값별: 답 있는 질문은 '정답 근거가 상위 3에 있고 1위 점수가 기준 이상'이어야 살아남는다.
    sweep = []
    for t in THRESHOLDS:
        kept = sum(1 for r in ans if r["rank"] and r["rank"] <= 3 and r["top_score"] >= t)
        rejected = sum(1 for r in none if r["top_score"] < t)
        sweep.append({"threshold": t, "answer_kept": kept, "none_rejected": rejected})

    print(f"\n=== 검색 정확도 (임베딩 {config.EMBED_MODEL}, 질문 {n}개) ===")
    for k in (1, 3, 5):
        mark = "  ← PER-003 목표 80%" if k == 3 else ""
        print(f"상위 {k} 정답률: {pct(top[k], n)}{mark}")
    print("\n분야·말투별 상위 3 정답률")
    for key in sorted(by):
        print(f"  {key:12} {pct(*by[key])}")
    print(f"\n근거 기준값별 (답 있는 질문 {n}개 / 자료에 없는 질문 {len(none)}개), 현재 기준값 {config.MIN_SCORE}")
    print("  기준값  답있는질문_살림  없는질문_걸러냄")
    for s in sweep:
        cur = "  ← 현재" if abs(s["threshold"] - config.MIN_SCORE) < 1e-9 else ""
        print(f"  {s['threshold']:.2f}    {pct(s['answer_kept'], n):16} {pct(s['none_rejected'], len(none))}{cur}")
    miss = [r for r in ans if not (r["rank"] and r["rank"] <= 3)]
    print(f"\n상위 3에 정답 근거가 없는 질문 {len(miss)}개")
    for r in miss:
        print(f"  {r['id']} [{r['style']}] {r['q']} → 순위 {r['rank']}, 1위: {r['top3'][0] if r['top3'] else '-'} ({r['top_score']})")

    summary = {"date": datetime.now().isoformat(timespec="seconds"), "embed_model": config.EMBED_MODEL,
               "min_score": config.MIN_SCORE, "answer_n": n, "none_n": len(none),
               "top1": top[1], "top3": top[3], "top5": top[5],
               "by_group_top3": {k: v for k, v in sorted(by.items())}, "threshold_sweep": sweep}
    out = Path(args.out) if args.out else ROOT / "eval" / "results" / f"retrieval_{datetime.now():%Y%m%d_%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
