"""학교 사이트 전체(메인 메뉴 + 학과·대학원 사이트)를 수집해 data/chunks_site.jsonl로 저장한다.

사용 (ask-campus 폴더에서):
  .venv/Scripts/python -m src.ingest.run_site                    # 게시판은 2025-03-01 이후 글
  .venv/Scripts/python -m src.ingest.run_site --since 2026-01-01 --max-pages 5
.env에 학교 계정이 있으면 로그인해서 로그인 전용 게시판도 읽는다.
그다음 색인: .venv/Scripts/python -m src.server.build_index
"""
import argparse
import json
from pathlib import Path

from .fetch import Fetcher
from .login_sources import LoginError, login
from .site_sources import departments, main_site

DATA = Path(__file__).resolve().parents[2] / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2025-03-01", help="게시판에서 이 날짜 이후 글만 (예전 공지가 섞이지 않게)")
    ap.add_argument("--max-pages", type=int, default=15, help="게시판마다 읽을 목록 최대 쪽 수 (한 쪽 10건)")
    args = ap.parse_args()
    f = Fetcher(delay=1.0, raw_dir=None)
    try:
        login(f)
        print("로그인 성공")
    except LoginError as e:
        print(f"로그인 없이 진행 ({e})")
    chunks = main_site(f, args.since, args.max_pages)
    print(f"메인 사이트: 청크 {len(chunks)}개")
    part = departments(f, args.since, args.max_pages)
    print(f"학과·대학원: 청크 {len(part)}개")
    out = DATA / "chunks_site.jsonl"
    with out.open("w", encoding="utf-8") as fp:
        for c in chunks + part:
            fp.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    print(f"청크 {len(chunks) + len(part)}개 → {out}")


if __name__ == "__main__":
    main()
