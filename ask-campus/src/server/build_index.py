"""data/chunks.jsonl을 SQLite chunk 테이블과 Chroma 'chunks' 컬렉션에 넣는다 (FR-016).

사용 (ask-campus 폴더에서): .venv/Scripts/python -m src.server.build_index
다시 실행하면 청크를 새로 넣는다 (FAQ·답변 대기는 그대로 둠).
"""
import json

from . import config, db, index


def main():
    db.init()
    rows = [json.loads(line) for line in config.CHUNKS_JSONL.open(encoding="utf-8")]
    rows = list({r["chunk_id"]: r for r in rows}.values())   # 같은 글이 두 번 수집된 경우 하나만
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
    vecs = index.embed([r["content"] for r in rows])
    col.add(ids=[r["chunk_id"] for r in rows], embeddings=vecs, documents=[r["content"] for r in rows],
            metadatas=[{"category": r["category"], "campus": r["metadata"].get("campus") or "공통",
                        "title": r["title"], "source_url": r["source_url"],
                        "menu_path": r["metadata"].get("menu_path") or "", "collected_at": r["collected_at"]}
                       for r in rows])
    print(f"청크 {len(rows)}개 색인 완료 → {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
