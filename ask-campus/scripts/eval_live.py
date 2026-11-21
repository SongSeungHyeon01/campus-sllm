"""실행 중인 서버에 평가 질문을 보내 채점하고, 틀린 답은 '답이 이상해요' 피드백으로 등록한다.

11/21 사용자 요청: 페르소나 50명 + 실제 질문 기록을 우리 서비스로 돌리고, 잘못된 답은 피드백에 적용해 고친다.
model_compare.py·eval_persona.py는 서버를 끄고 DB 복사본·고정 시각으로 돌리지만, 이 스크립트는 실제 서버(지금 시각)를 쓴다.

사용 (ask-campus 폴더에서):
  .venv/Scripts/python scripts/eval_live.py 결과.json eval/questions_persona50.jsonl eval/questions_reallog.jsonl [--feedback]
  --feedback: 틀린 답(FAIL)을 /api/v1/feedback으로 등록한다 (관리 웹 '답변 피드백'에 쌓임)

채점
- answer: 답변 유형이 '문서'·'FAQ'이고 expect 중 하나가 답에 있음. expect_all은 묶음마다 하나씩
- none: '근거없음'
- clarify: 되묻기
- trap: 사람이 확인 (CHECK)
"""
import json
import sys
import time
import urllib.request
from collections import defaultdict

SERVER = "http://localhost:8000"


_sent: list[float] = []


def post(path: str, body: dict) -> dict:
    """서버는 접속 주소마다 분당 20번까지 받는다 (app.py rate_limited). 분당 18번으로 맞추고, 그래도 막히면 기다렸다 다시."""
    import urllib.error
    while True:
        now = time.time()
        _sent[:] = [t for t in _sent if now - t < 60]
        if len(_sent) >= 18:
            time.sleep(60 - (now - _sent[0]) + 0.5)
            continue
        _sent.append(time.time())
        req = urllib.request.Request(SERVER + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(30)


def grade(item: dict, r: dict) -> str:
    kind, ans, typ = item["kind"], r.get("answer", ""), r.get("answer_type")
    if kind == "trap":
        return "CHECK"
    if kind == "none":
        return "PASS" if typ == "근거없음" else "FAIL"
    if kind == "clarify":
        return "PASS" if r.get("clarify") else "FAIL"
    # 학식처럼 코드가 '그날 식단이 없다'고 알리는 답은 근거없음 유형이어도 내용이 맞으면 통과
    if r.get("clarify") or (typ == "근거없음" and ans.startswith("해당 정보를 찾을 수 없습니다")):
        return "FAIL"
    flat = ans.replace("\n", " ")
    if item.get("expect_all"):
        return "PASS" if all(any(e in flat for e in grp) for grp in item["expect_all"]) else "FAIL"
    return "PASS" if any(e in flat for e in item.get("expect", [])) else "FAIL"


def main():
    out_path, files = sys.argv[1], [a for a in sys.argv[2:] if not a.startswith("--")]
    feedback = "--feedback" in sys.argv
    items = [json.loads(l) for f in files for l in open(f, encoding="utf-8") if l.strip()]
    results = []
    for it in items:
        t0 = time.time()
        r = post("/api/v1/ask", {"question": it["q"], "campus": it["campus"], "department": it.get("department")})
        it_res = {**it, "answer_type": r.get("answer_type"), "answer": r.get("answer"), "log_id": r.get("log_id"),
                  "clarify": bool(r.get("clarify")), "sec": round(time.time() - t0, 1),
                  "sources": [s.get("label") or s.get("title") for s in r.get("sources") or []][:3]}
        it_res["result"] = grade(it, r)
        results.append(it_res)
        mark = {"PASS": "  ", "FAIL": "✗ ", "CHECK": "? "}[it_res["result"]]
        print(f"{mark}{it['id']} [{it['kind']}] {it['q']} → {it_res['answer_type']}"
              + ("" if it_res["result"] == "PASS" else "\n      " + (it_res["answer"] or "").replace("\n", " / ")[:220]))
        if feedback and it_res["result"] == "FAIL" and it_res["log_id"]:
            want = it.get("expect_all") or it.get("expect") or []
            note = {"none": "자료에 없는 내용이라 '찾을 수 없음'으로 답해야 함",
                    "clarify": "질문이 애매해서 되물어야 함"}.get(it["kind"], f"답에 이 값이 있어야 함: {str(want)[:120]}")
            post("/api/v1/feedback", {"log_id": it_res["log_id"], "comment": f"[{it['id']} 평가] {note}"[:300]})
    json.dump(results, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def summary(key, label):
        agg = defaultdict(lambda: [0, 0])
        for x in results:
            if x["result"] == "CHECK":
                continue
            k = key(x)
            agg[k][1] += 1
            agg[k][0] += x["result"] == "PASS"
        print(f"\n{label}")
        for k, (p, n) in sorted(agg.items(), key=lambda kv: str(kv[0])):
            print(f"  {str(k):<14} {p}/{n}")
    summary(lambda x: x["source"], "출처별 (맞음/채점)")
    summary(lambda x: x["kind"], "종류별")
    per = [x for x in results if x.get("persona")]
    if per:
        results_all = results[:]
        results[:] = per
        summary(lambda x: x["persona"]["style"], "말투별 (페르소나)")
        summary(lambda x: "유학생" if x["persona"]["intl"] else "국내", "유학생 여부")
        summary(lambda x: x["persona"]["tech"], "기술 숙련도")
        summary(lambda x: x["persona"]["grade"], "학년")
        results[:] = results_all
    print(f"\n사람 확인(trap) {sum(x['result'] == 'CHECK' for x in results)}개, 결과 파일: {out_path}")


if __name__ == "__main__":
    main()
