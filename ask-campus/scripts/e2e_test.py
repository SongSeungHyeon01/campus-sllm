"""조교 답변 흐름 전체를 실행 중인 서버에 시험한다 (FR-005, FR-028, FR-029).

1) 자료에 없는 질문 → 근거없음 + 답변 대기 자동 등록
2) 비슷하게 바꾼 질문 → 같은 답변 대기에 묶여 '같은 질문 수'가 늘어남
3) 관리 웹 로그인 → 답변 대기 목록 → 답변 등록
4) 같은 질문과 바꾼 질문 → 'FAQ' 답변 ('학과 조교 답변 · 등록일')
5) 입력 검사 (빈 질문, 201자)

사용 (ask-campus 폴더에서): set ASK_ADMIN_PASSWORD=... 후
  .venv/Scripts/python scripts/e2e_test.py [서버 주소]
※ 시험 데이터가 DB에 남는다. 시연 전에는 data/askcampus.db의 faq·pending_question을 비우거나 DB를 새로 만든다.
"""
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

B = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
Q1 = "졸업작품 전시회 장소가 어디야?"
Q2 = "졸업작품 전시회는 어디서 해?"
ANSWER = "(시험용 답변) 졸업작품 전시회 장소는 학과 사무실 안내를 따릅니다."
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def ask(q):
    req = urllib.request.Request(B + "/api/v1/ask", method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"question": q, "campus": "아산"}).encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def pending_rows(op):
    html = op.open(B + "/admin").read().decode()
    return {int(pid): (q, int(n)) for q, n, pid in
            re.findall(r"<td>(.*?)</td>\s*<td>(\d+)건</td>.*?/admin/pending/(\d+)", html, re.S)}


def main():
    s, r = ask(Q1)
    check("자료에 없는 질문 → 근거없음 + 답변 대기 등록", s == 200 and r["answer_type"] == "근거없음" and r["pending_registered"],
          f'{r.get("answer_type")}, {r.get("elapsed_ms")}ms')
    ask(Q2)

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(B + "/admin/login", data=urllib.parse.urlencode({"password": os.environ["ASK_ADMIN_PASSWORD"]}).encode())
    rows = pending_rows(op)
    target = next((pid for pid, (q, _) in rows.items() if "졸업작품" in q), None)
    check("관리 웹 로그인 후 답변 대기 목록에 보임", target is not None, f"{len(rows)}건")
    if target is None:
        return
    check("비슷한 질문은 같은 답변 대기에 묶임", rows[target][1] >= 2, f"같은 질문 {rows[target][1]}건")

    form = {"question": Q1, "answer": ANSWER, "category": "동아리·행사", "campus": ""}
    done = op.open(B + f"/admin/pending/{target}/answer", data=urllib.parse.urlencode(form).encode()).geturl()
    check("답변 등록 → FAQ 관리로 이동", "faqs?done=1" in done)
    check("답변한 질문은 대기 목록에서 빠짐", target not in pending_rows(op))

    for q in (Q1, Q2):
        s, r = ask(q)
        label = (r.get("sources") or [{}])[0].get("label", "")
        check(f"'{q}' → 조교 답변(FAQ)", r.get("answer_type") == "FAQ" and r.get("answer") == ANSWER,
              f'{r.get("answer_type")}, {label}, {r.get("elapsed_ms")}ms')

    s, r = ask("")
    check("빈 질문 → 400 INVALID_QUESTION", s == 400 and r["error"]["code"] == "INVALID_QUESTION")
    s, _ = ask("가" * 201)
    check("201자 질문 → 400", s == 400)

    print(f"\n{sum(results)}/{len(results)} 통과")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
