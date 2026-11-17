# 조교 답변(FAQ)을 처음 등록한 직후 질문하면 500 오류 (Chroma "Nothing found on disk")

- **발생 시각**: 2026-10-12
- **위치**: `ask-campus/src/server/index.py` `search()` → `col.query(...)` (FAQ 컬렉션), `POST /api/v1/ask`
- **상태**: 우회함 (FAQ·답변 대기를 Chroma에서 SQLite로 옮김)

## 증상

관리 웹에서 첫 FAQ를 등록한 뒤 `/api/v1/ask`를 호출하면 500 Internal Server Error.

```
File "src\server\rag.py", line 60, in ask
    faq_hit = next(iter(index.search("faq", qvec, 1)), None)
File "src\server\index.py", line 46, in search
    res = col.query(query_embeddings=[query_vec], n_results=min(k, col.count()), where=where)
chromadb.errors.InternalError: Error executing plan: Internal error: Error creating hnsw segment reader: Nothing found on disk
```

## 원인 조사

- 처음에는 응답이 JSON이 아니라는 클라이언트 오류만 보였다. 서버 출력을 `grep`으로 걸러 실행해서 로그가 버퍼에 막혀 보이지 않았다 → 서버를 `> data/server.log`로 직접 기록하도록 다시 실행해 위 스택을 확인했다.
- 같은 서버 프로세스 안에서 `upsert`로 FAQ 1건을 넣은 바로 다음 `query`에서 실패. 비어 있던 컬렉션에 처음 들어간 항목의 HNSW 인덱스가 아직 디스크에 없는 상태에서 읽으려다 실패하는 것으로 보인다 (가설, chromadb 1.5.9).
- 같은 시각 청크 컬렉션(빌드 때 한꺼번에 넣고 서버에서는 읽기만 함)은 문제없이 동작했다.
- 시험 중에 다른 프로세스(정리 스크립트)가 같은 Chroma 폴더를 함께 고친 적도 있어, 여러 프로세스가 한 PersistentClient를 쓰는 것도 위험 요인으로 판단했다.

## 근본 원인

미확인. 가장 유력한 가설: chromadb 1.5.9에서 빈 컬렉션에 첫 항목을 넣은 직후 검색할 때 HNSW 세그먼트를 읽지 못하는 문제.

## 해결 방법

- FAQ와 답변 대기 질문은 수백 건 수준이라 벡터 DB가 필요 없다고 판단해 **SQLite `vec` 열(float32)에 임베딩을 저장하고 numpy 내적으로 유사도를 계산**하도록 바꿨다 (`db.py`, `rag.py`).
- Chroma는 `build_index.py`가 만드는 청크 컬렉션에만 쓴다 (서버에서는 읽기 전용).
- 시험 데이터와 예전 `faq`·`pending` 컬렉션은 지웠다.
- 다시 시험: `scripts/e2e_test.py` 9/9 통과 (FAQ 등록 직후 같은 질문·바꾼 질문 모두 FAQ로 답함).

## 재발 방지

- 서버가 실행 중일 때 다른 프로세스에서 같은 Chroma 폴더를 고치지 않는다.
- 서버 로그는 파일로 남긴다 (`PYTHONUNBUFFERED=1`, `> data/server.log`).
