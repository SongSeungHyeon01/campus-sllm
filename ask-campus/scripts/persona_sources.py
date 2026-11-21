"""페르소나 평가 질문을 만들 원문 자료를 뽑는다 (eval/persona_prompt.md의 [원문 자료]에 넣을 것).

사용 (ask-campus 폴더에서): .venv/Scripts/python scripts/persona_sources.py 5 > 결과.md
- 묶음 수만큼, 묶음마다 원문 16건을 분야·캠퍼스가 고르게 뽑는다 (같은 시드면 같은 결과).
- 학생 Q&A(개인 사정이 섞임)와 매주 바뀌는 구내식당 메뉴는 뺀다.
- 날짜·금액·전화번호처럼 답에 나올 값이 있는 조각만 고른다 (expect를 만들 수 있게).
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["chunks.jsonl", "chunks_login.jsonl", "chunks_site.jsonl"]
VALUE = re.compile(r"\d{1,4}[.\-/년]\s*\d{1,2}|\d{1,3}(,\d{3})+원|\d+만\s*원|0\d{1,2}-\d{3,4}-\d{4}|\d{1,2}:\d{2}|\d+학점|\d+학기")
# 묶음 16건의 분야 배분
PLAN = [("학사일정", 3), ("학사공지", 3), ("일반공지", 2), ("장학", 2), ("통학버스", 2), ("동아리", 1), ("학사", 2), ("FAQ", 1)]


def domain(r: dict) -> str | None:
    cat, title, menu = r["category"], r["title"], r["metadata"].get("menu_path") or ""
    if cat == "Q&A" or "구내식당" in title or "cafeteria" in r["source_url"]:
        return None
    if cat == "통학버스":
        return "통학버스"
    if cat.startswith("동아리"):
        return "동아리"
    if cat == "FAQ":
        return "FAQ"
    if title.startswith("학사일정"):
        return "학사일정"
    if "장학" in menu or "scholarship" in r["source_url"] or "장학" in title:
        return "장학"
    if "학사공지" in menu or "/academic.do" in r["source_url"]:
        return "학사공지"
    if "일반공지" in menu or "/common.do" in r["source_url"]:
        return "일반공지"
    if cat == "학사정보" or "/u1/academic/" in r["source_url"]:
        return "학사"
    return None


def main():
    batches = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    rows = []
    for f in FILES:
        p = ROOT / "data" / f
        if p.exists():
            rows += [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
    pool: dict[str, list[dict]] = {}
    for r in rows:
        d = domain(r)
        short_ok = d == "학사일정"                 # 학사일정은 일정 하나가 한 줄짜리 조각
        value_ok = d == "동아리" or VALUE.search(r["content"])   # 동아리는 이름·장소가 답이라 숫자가 없어도 됨
        if d and (short_ok or len(r["content"]) >= 120) and value_ok and r["title"] != "동아리현황":
            pool.setdefault(d, []).append(r)
    rnd = random.Random(1120)
    for v in pool.values():
        rnd.shuffle(v)
    used = set()
    for b in range(batches):
        print(f"# 묶음 {b + 1}\n")
        n = 0
        for d, k in PLAN:
            picks = [r for r in pool.get(d, []) if r["chunk_id"] not in used][:k]
            for r in picks:
                used.add(r["chunk_id"])
                n += 1
                campus = r["metadata"].get("campus") or "공통"
                body = re.sub(r"\s+", " ", r["content"])[:520]
                print(f"## S{b + 1}-{n:02d} | 분야: {d} | 캠퍼스: {campus} | chunk_id: {r['chunk_id']}\n제목: {r['title']}\n내용: {body}\n")


if __name__ == "__main__":
    main()
