"""수집 결과를 SQLite chunk 테이블과 Chroma 'chunks' 컬렉션에 넣는다 (FR-016).

넣는 파일 (있는 것만): data/chunks.jsonl(공개 페이지), chunks_login.jsonl(FAQ·Q&A), chunks_site.jsonl(사이트 전체·학과)

사용 (ask-campus 폴더에서): .venv/Scripts/python -m src.server.build_index
- 서버가 꺼져 있을 때 직접 실행한다. 서버가 켜져 있으면 scripts/refresh.py가 서버 안에서 main()을 부른다
  (Chroma를 두 프로세스가 동시에 쓰면 안전하지 않아서).
- 다시 실행하면 청크를 새로 넣는다 (FAQ·답변 대기는 그대로 둠).
"""
import json

from . import config, db, index


def load_rows() -> list[dict]:
    rows = []
    for path in (config.CHUNKS_JSONL, config.CHUNKS_LOGIN_JSONL, config.CHUNKS_SITE_JSONL):
        if path.exists():
            rows += [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    return list({r["chunk_id"]: r for r in rows}.values())   # 같은 글이 두 번 수집된 경우 하나만


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
