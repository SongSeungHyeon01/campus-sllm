"""이미 수집한 자료(data/chunks*.jsonl)에 사람 이름 가림 규칙을 다시 적용한다 (다시 수집하지 않고).

11/21: 열린 총장 게시판 목록('비밀글 이름 26.10.16'), 학과 자료실의 학생 글('1학년 이름 입니다'),
홈페이지 수정 요청 게시판 글이 가려지지 않은 채 들어간 것을 확인했다. 수집 코드(site_sources.scrub_names)를 고친 뒤
이미 모은 자료에도 같은 규칙을 적용한다. 바뀐 조각 수만 출력하고 내용은 출력하지 않는다.

사용 (ask-campus 폴더에서): .venv/Scripts/python scripts/rescrub.py
다음에 색인을 다시 만든다 (서버가 켜져 있으면 scripts/refresh.py와 같은 /internal/reindex).
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ingest.login_sources import mask  # noqa: E402
from src.ingest.site_sources import STUDENT_BOARDS, scrub_names  # noqa: E402

FILES = ["chunks.jsonl", "chunks_login.jsonl", "chunks_site.jsonl"]


def main():
    total = 0
    for name in FILES:
        path = ROOT / "data" / name
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
        changed = 0
        for r in rows:
            private = bool(STUDENT_BOARDS.search(urlparse(r.get("source_url", "")).path))
            for key in ("content", "title"):
                before = r.get(key) or ""
                after = scrub_names(mask(before) if private else before, board_list=private)
                if after != before:
                    r[key] = after
                    changed += 1
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"{name}: {len(rows)}개 중 {changed}칸 가림")
        total += changed
    print(f"합계 {total}칸")


if __name__ == "__main__":
    main()
