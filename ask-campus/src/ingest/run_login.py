"""로그인이 필요한 FAQ·Q&A를 수집해 data/chunks_login.jsonl로 저장한다.

사용 (ask-campus 폴더에서, .env에 U1_ID·U1_PW 필요):
  .venv/Scripts/python -m src.ingest.run_login                 # FAQ 전체 + Q&A 2021년 이후 답변 달린 글
  .venv/Scripts/python -m src.ingest.run_login --qna-pages 2   # Q&A는 목록 2쪽만 (시험용)
그다음 색인: .venv/Scripts/python -m src.server.build_index (chunks.jsonl과 함께 넣음)
"""
import argparse
import json
from pathlib import Path

from .fetch import Fetcher
from .login_sources import faq, login, qna

DATA = Path(__file__).resolve().parents[2] / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qna-pages", type=int, default=None, help="Q&A 목록을 몇 쪽까지 읽을지 (기본: since까지 전부)")
    ap.add_argument("--since", default="2021-01-01", help="이 날짜 이전 Q&A는 넣지 않음 (예전 규정이 섞이지 않게)")
    args = ap.parse_args()
    f = Fetcher(delay=1.0, raw_dir=None)          # 개인정보가 섞일 수 있어 원본 HTML은 저장하지 않음
    login(f)
    print("로그인 성공. 수집 시작 (요청 간격 1초)")
    chunks = faq(f)
    print(f"  FAQ: 청크 {len(chunks)}개")
    part, stat = qna(f, args.qna_pages, args.since)
    print(f"  Q&A: 청크 {len(part)}개 {stat}")
    out = DATA / "chunks_login.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fp:
        for c in chunks + part:
            fp.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    print(f"청크 {len(chunks) + len(part)}개 → {out}")


if __name__ == "__main__":
    main()
