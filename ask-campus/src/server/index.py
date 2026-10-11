"""임베딩(KURE-v1)과 벡터 DB(Chroma). 컬렉션 3개: 청크, FAQ, 답변 대기 질문."""
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from . import config


@lru_cache(maxsize=1)
def embedder() -> SentenceTransformer:
    if _cuda():
        import torch
        # fp16으로 올려 VRAM을 아낀다 (sLLM과 같은 8GB GPU를 나눠 씀)
        return SentenceTransformer(config.EMBED_MODEL, device="cuda", model_kwargs={"dtype": torch.float16})
    return SentenceTransformer(config.EMBED_MODEL, device="cpu")


def _cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def embed(texts: list[str]) -> list[list[float]]:
    return embedder().encode(texts, normalize_embeddings=True, batch_size=16).tolist()


@lru_cache(maxsize=1)
def _client():
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def collection(name: str):
    """name: chunks / faq / pending. 코사인 유사도 사용."""
    return _client().get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def search(name: str, query_vec: list[float], k: int, where: dict | None = None) -> list[dict]:
    col = collection(name)
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[query_vec], n_results=min(k, col.count()), where=where)
    hits = []
    for i, doc_id in enumerate(res["ids"][0]):
        hits.append({"id": doc_id, "score": 1 - res["distances"][0][i],
                     "document": res["documents"][0][i], "meta": res["metadatas"][0][i]})
    return hits
