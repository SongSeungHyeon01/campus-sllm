"""수집을 실행해 청크를 data/chunks.jsonl로 저장한다.

사용 (ask-campus 폴더에서): .venv/Scripts/python -m src.ingest.run [--notice-pages 2]
"""
import argparse
import json
from pathlib import Path

from .fetch import Fetcher
from .sources import collect_all

DATA = Path(__file__).resolve().parents[2] / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notice-pages", type=int, default=2, help="게시판마다 읽을 목록 쪽 수 (한 쪽 10건)")
    args = ap.parse_args()
    f = Fetcher(delay=1.0, raw_dir=DATA / "raw")
    print("수집 시작 (요청 간격 1초)")
    chunks = collect_all(f, args.notice_pages)
    out = DATA / "chunks.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fp:
        for c in chunks:
            fp.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    print(f"청크 {len(chunks)}개 → {out}")


if __name__ == "__main__":
    main()
