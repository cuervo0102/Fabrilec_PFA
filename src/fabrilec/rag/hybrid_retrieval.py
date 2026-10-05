import os
import pickle

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src.fabrilec.config import CHROMA_PATH, BM25_CACHE_PATH

COLLECTION_NAME = "fabrilec_tenders"

RRF_K = 60


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class HybridRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_collection(COLLECTION_NAME)
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self._load_or_build_bm25()

    def _load_or_build_bm25(self):
        if os.path.exists(BM25_CACHE_PATH):
            with open(BM25_CACHE_PATH, "rb") as f:
                cached = pickle.load(f)
            self.chunk_ids = cached["chunk_ids"]
            self.chunk_texts = cached["chunk_texts"]
            self.chunk_metadatas = cached["chunk_metadatas"]
            self.bm25 = cached["bm25"]
            return

        print("Building BM25 index (first run)...")
        all_data = self.collection.get(include=["documents", "metadatas"])
        self.chunk_ids = all_data["ids"]
        self.chunk_texts = all_data["documents"]
        self.chunk_metadatas = all_data["metadatas"]

        tokenized_corpus = [_tokenize(t) for t in self.chunk_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        os.makedirs(os.path.dirname(BM25_CACHE_PATH), exist_ok=True)
        with open(BM25_CACHE_PATH, "wb") as f:
            pickle.dump({
                "chunk_ids": self.chunk_ids,
                "chunk_texts": self.chunk_texts,
                "chunk_metadatas": self.chunk_metadatas,
                "bm25": self.bm25,
            }, f)

    def _semantic_search(self, query: str, top_k: int) -> list[str]:
        query_embedding = self.model.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_embedding, n_results=top_k)
        return results["ids"][0]

    def _bm25_search(self, query: str, top_k: int) -> list[str]:
        tokenized_query = _tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.chunk_ids[i] for i in ranked_indices]

    def search(self, query: str, top_k: int = 5, candidate_pool: int = 20) -> list[dict]:
        semantic_ids = self._semantic_search(query, candidate_pool)
        bm25_ids = self._bm25_search(query, candidate_pool)

        rrf_scores = {}
        for rank, chunk_id in enumerate(semantic_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        for rank, chunk_id in enumerate(bm25_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)

        ranked_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

        id_to_index = {cid: i for i, cid in enumerate(self.chunk_ids)}
        results = []
        for chunk_id in ranked_ids:
            idx = id_to_index[chunk_id]
            results.append({
                "chunk_id": chunk_id,
                "text": self.chunk_texts[idx],
                "metadata": self.chunk_metadatas[idx],
                "rrf_score": rrf_scores[chunk_id],
            })
        return results


if __name__ == "__main__":
    retriever = HybridRetriever()
    query = "délai de livraison"
    results = retriever.search(query, top_k=3)
    print(f"Query: {query!r}\n")
    for r in results:
        print(f"[{r['metadata']['document_type']}] {r['metadata']['relative_path']} (score={r['rrf_score']:.4f})")
        print(f"  {r['text'][:150]}...\n")