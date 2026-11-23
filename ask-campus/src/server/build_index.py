"""수집 결과를 SQLite chunk 테이블과 Chroma 'chunks' 컬렉션에 넣는다 (FR-016).

넣는 파일 (있는 것만): data/chunks.jsonl(공개 페이지), chunks_login.jsonl(FAQ·Q&A), chunks_site.jsonl(사이트 전체·학과)

사용 (ask-campus 폴더에서): .venv/Scripts/python -m src.server.build_index
- 서버가 꺼져 있을 때 직접 실행한다. 서버가 켜져 있으면 scripts/refresh.py가 서버 안에서 main()을 부른다
  (Chroma를 두 프로세스가 동시에 쓰면 안전하지 않아서).
- 다시 실행하면 청크를 새로 넣는다 (FAQ·답변 대기는 그대로 둠).
"""
import json
import re

from . import config, db, index

# 한 학생에게만 맞거나 때가 지난 Q&A 답은 색인에 넣지 않는다 (원본 jsonl에는 그대로 있음).
# 11/22 평가: '국장 언제 들어와요?'에 다른 학생의 지급일을, '복학 신청 기간'에 2023년 날짜를 올해 것처럼 답했다.
_PERSONAL = re.compile(
    r"유선|전화(로)?\s*(안내|답변|상담)|조회\s*결과|확인\s*결과|(문의하신|해당|현재)\s*학생(은|의|이)|○○○\s*학생|학생의\s*경우"
    r"|(지급|입금)\s*(될\s*)?(예정|되었|완료|해드렸)|금일|금주|(다음|이번)\s*주|확인해\s*보겠|아직\s*올라가지"
    r"|20\d{2}\s*[.\-년]|(?<!\d)\d{1,2}월\s*\d{1,2}일|(?<!\d)\d{1,2}/\d{1,2}(?!\d)|\d{1,2}\.\s?\d{1,2}\(|어학연수|취소되었")


def drop_personal_qna(rows: list[dict]) -> list[dict]:
    answers: dict[str, str] = {}
    for r in rows:
        if r["category"] == "Q&A":
            answers[r["source_url"]] = answers.get(r["source_url"], "") + "\n" + r["content"]
    bad = {u for u, t in answers.items() if _PERSONAL.search(t.split("학교 답변:", 1)[-1])}
    return [r for r in rows if not (r["category"] == "Q&A" and r["source_url"] in bad)]


# 학생이 자기 서류를 내거나 사정을 적은 글 (복학신청서류접수 게시판, 총장에게 쓴 편지). 안내가 아니라서 넣지 않는다.
_STUDENT_PAPER = re.compile(r"/reinstatement\.do\?.*articleNo=")


def drop_student_papers(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not (_STUDENT_PAPER.search(r["source_url"] or "") or "총장님께" in r["content"])]


def load_rows() -> list[dict]:
    rows = []
    for path in (config.CHUNKS_JSONL, config.CHUNKS_LOGIN_JSONL, config.CHUNKS_SITE_JSONL):
        if path.exists():
            rows += [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    rows = drop_student_papers(rows)
    return drop_personal_qna(list({r["chunk_id"]: r for r in rows}.values()))   # 같은 글이 두 번 수집된 경우 하나만


def main() -> int:
    db.init()
    rows = load_rows()
    # 11/19: 임베딩 계산(1~2분)을 먼저 끝낸 뒤 교체한다. 예전엔 컬렉션을 먼저 지워서 그동안 서버가 답을 못 했다
    vecs = index.embed([r["content"] for r in rows])
    ts = db.now()
    with db.connect() as con:
        con.execute("DELETE FROM chunk")
        for r in rows:
            m = r["metadata"]
            con.execute("INSERT INTO chunk VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (r["chunk_id"], r["category"], m.get("campus"), r["title"], r["content"], r["source_url"],
                         m.get("menu_path"), m.get("posted_at"), r["collected_at"], ts))
    try:
        index._client().delete_collection("chunks")
    except Exception:
        pass
    col = index.collection("chunks")
    for i in range(0, len(rows), 1000):                        # Chroma 한 번에 넣는 개수 제한 대비
        part = rows[i:i + 1000]
        col.add(ids=[r["chunk_id"] for r in part], embeddings=vecs[i:i + 1000], documents=[r["content"] for r in part],
                metadatas=[{"category": r["category"], "campus": r["metadata"].get("campus") or "공통",
                            "title": r["title"], "source_url": r["source_url"],
                            "menu_path": r["metadata"].get("menu_path") or "", "collected_at": r["collected_at"]}
                           for r in part])
    print(f"청크 {len(rows)}개 색인 완료 → {config.CHROMA_DIR}")
    return len(rows)


if __name__ == "__main__":
    main()
