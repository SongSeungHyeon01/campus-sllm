"""실행 중인 서버에 대표 질문을 보내 답변 유형·출처·시간을 확인한다.

사용 (ask-campus 폴더에서): .venv/Scripts/python scripts/smoke_test.py [서버 주소]
"""
import json
import sys
import urllib.request

SERVER = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")

QUESTIONS = [
    ("수강정정 언제까지야?", "아산"),
    ("2학기 일반휴학 신청 기간 알려줘", "아산"),
    ("아산캠 주말에 천안터미널에서 학교 가는 첫차 몇 시야?", "아산"),
    ("영동역에서 학교 가는 통학버스 시간 알려줘", "영동"),
    ("등록금 환불 2/3선 언제야?", "아산"),
    ("학습법 공모전 상금 얼마야?", "아산"),
    ("국악 동아리 있어?", "영동"),
    # 아래는 수집한 자료에 없는 질문 → 근거없음 + 답변 대기 자동 등록이 나와야 함
    ("편입생 전공 학점 인정 몇 학점까지야?", "아산"),
    ("기숙사 신청 언제 해?", "아산"),
    ("학식 메뉴 알려줘", "아산"),
    ("도서관 몇 시에 닫아?", "아산"),
]


def ask(q: str, campus: str) -> dict:
    req = urllib.request.Request(f"{SERVER}/api/v1/ask", method="POST",
                                 data=json.dumps({"question": q, "campus": campus}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    for q, campus in QUESTIONS:
        r = ask(q, campus)
        print(f"\nQ ({campus}) {q}")
        print(f"  [{r['answer_type']}] {r['elapsed_ms']}ms  pending={r['pending_registered']}")
        print("  " + r["answer"].replace("\n", "\n  ")[:500])
        for s in r["sources"]:
            print(f"  - 출처: {s['title']} | {s.get('menu_path') or ''}")


if __name__ == "__main__":
    main()
