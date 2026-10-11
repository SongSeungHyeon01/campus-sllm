"""시간에 따라 답이 달라지는 통학버스 질문을 여러 시각으로 시험한다 (서버 없이 직접 실행).

기대값은 2026-10-12 수집한 아산캠퍼스 시간표 기준이다 (평일: 학기 중 1,2호차 두정역 08:00, 08:30, 09:30, 10:15 …
주말: 주말·공휴일·방학 시간표). 시간표가 바뀌면 EXPECT를 고친다.
GPU 메모리 때문에 서버를 끄고 실행한다: .venv/Scripts/python scripts/time_test.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.server import db, rag  # noqa: E402

Q = "방금 막 두정역에 도착했는데 가장 빠른 시간의 버스 시간표 좀 알려줘"
MON, SAT = (2026, 10, 12), (2026, 10, 17)
CASES = [  # (질문, 시각, 캠퍼스, 기대: 답에 들어 있어야 할 글자)
    (Q, (*MON, 7, 37), "아산", "08:00"),                      # 월요일 아침
    (Q, (*MON, 8, 10), "아산", "08:30"),
    (Q, (*MON, 10, 0), "아산", "10:15"),
    (Q, (*MON, 13, 0), "아산", "13:55"),
    (Q, (*SAT, 10, 0), "아산", "10:50"),                      # 토요일: 주말·공휴일 시간표
    (Q, (*MON, 21, 0), "아산", "끝났"),                       # 막차 이후: 오늘 운행 끝 + 첫차 안내
    ("아산캠 주말에 천안터미널에서 학교 가는 첫차 몇 시야?", (*MON, 7, 37), "아산", "07:50"),  # 월요일에 주말을 물음
    ("토요일에 두정역에서 학교 가는 가장 빠른 차 알려줘", (*MON, 7, 37), "아산", "08:00"),   # 오늘이 아닌 날 → 첫차
    ("두정역에서 학교 가는 막차 몇 시야?", (*MON, 7, 37), "아산", "19:30"),
    ("영동역에서 학교 가는 통학버스 시간 알려줘", (*MON, 7, 37), "영동", "8:00"),           # 전체 시간 목록
]


def main():
    ok = 0
    for q, t, campus, expect in CASES:
        now = datetime(*t, tzinfo=db.KST)
        rag._now = lambda now=now: now
        r = rag.ask(q, None, campus)
        hit = expect in r["answer"]
        ok += hit
        print(f"{'PASS' if hit else 'FAIL'} [{now:%a %H:%M}] {q[:24]} → 기대 {expect} | {r['answer_type']} {r['elapsed_ms']}ms")
        print("     " + r["answer"].replace("\n", " / ")[:150])
    print(f"{ok}/{len(CASES)} 통과")


if __name__ == "__main__":
    main()
