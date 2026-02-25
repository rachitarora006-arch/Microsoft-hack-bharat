"""
rag_module.py — News ingestion, embedding, and hybrid search via Pathway.

Provides:
  - Document chunking and embedding using SentenceTransformers
  - In-memory vector index (BruteForce KNN)
  - BM25 text search fallback
  - Hybrid retrieval combining both approaches
  - Auto-updating index as new news arrives

Uses Pathway's streaming primitives so the index updates in real time.
"""


import logging
import json
import os
import math
from collections import defaultdict

import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  DOCUMENT STORE (In-Memory, Streaming)
# ═══════════════════════════════════════════════════════════

class DocumentStore:
    """
    Lightweight in-memory document store with vector + BM25 search.
    Updated in real-time as new documents arrive from the Pathway stream.
    """

    def __init__(self):
        self.documents: list[dict] = []
        self.embeddings: list[list[float]] = []
        self.bm25_index: dict[str, list[int]] = defaultdict(list)
        self._embedder = None

    def _get_embedder(self):
        """Lazy-load the sentence transformer embedder."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(config.EMBEDDING_MODEL)
                logger.info(f"✅ Loaded embedding model: {config.EMBEDDING_MODEL}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load embedding model: {e}. Using TF-IDF fallback.")
                self._embedder = "fallback"
        return self._embedder

    def add_document(self, title: str, body: str, source: str, published_at: str):
        """Add a document, chunk it, embed it, and index it."""
        full_text = f"{title}. {body}"
        chunks = self._chunk_text(full_text)

        for chunk in chunks:
            doc_id = len(self.documents)
            doc = {
                "id": doc_id,
                "title": title,
                "body": body,
                "chunk": chunk,
                "source": source,
                "published_at": published_at,
            }
            self.documents.append(doc)

            # Embed
            embedding = self._embed(chunk)
            self.embeddings.append(embedding)

            # BM25 index
            tokens = self._tokenize(chunk)
            for token in set(tokens):
                self.bm25_index[token].append(doc_id)

        logger.info(f"📄 Indexed document: '{title}' ({len(chunks)} chunks)")

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks by word count."""
        words = text.split()
        chunks = []
        step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
        step = max(step, 1)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + config.CHUNK_SIZE])
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]

    def _embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        embedder = self._get_embedder()
        if embedder == "fallback":
            return self._tfidf_embed(text)
        try:
            vec = embedder.encode(text, show_progress_bar=False).tolist()
            return vec
        except Exception:
            return self._tfidf_embed(text)

    def _tfidf_embed(self, text: str) -> list[float]:
        """Fallback: simple hash-based embedding."""
        vec = [0.0] * config.EMBEDDING_DIMENSION
        tokens = self._tokenize(text)
        for token in tokens:
            h = hash(token) % config.EMBEDDING_DIMENSION
            vec[h] += 1.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        return [w.lower().strip(".,!?;:'\"()[]{}") for w in text.split() if len(w) > 2]

    def search_vector(self, query: str, top_k: int = None) -> list[dict]:
        """Vector similarity search (cosine)."""
        if not self.documents:
            return []
        top_k = top_k or config.RAG_TOP_K
        query_vec = self._embed(query)
        scores = []
        for i, doc_vec in enumerate(self.embeddings):
            score = self._cosine_sim(query_vec, doc_vec)
            scores.append((score, i))
        scores.sort(reverse=True)
        return [
            {**self.documents[idx], "score": round(score, 4), "method": "vector"}
            for score, idx in scores[:top_k]
        ]

    def search_bm25(self, query: str, top_k: int = None) -> list[dict]:
        """BM25-style keyword search."""
        if not self.documents:
            return []
        top_k = top_k or config.RAG_TOP_K
        query_tokens = self._tokenize(query)
        doc_scores = defaultdict(float)
        for token in query_tokens:
            if token in self.bm25_index:
                idf = math.log(len(self.documents) / (1 + len(self.bm25_index[token])))
                for doc_id in self.bm25_index[token]:
                    doc_scores[doc_id] += idf
        ranked = sorted(doc_scores.items(), key=lambda x: -x[1])
        return [
            {**self.documents[doc_id], "score": round(score, 4), "method": "bm25"}
            for doc_id, score in ranked[:top_k]
        ]

    def hybrid_search(self, query: str, top_k: int = None) -> list[dict]:
        """Combine vector and BM25 results with reciprocal rank fusion."""
        top_k = top_k or config.RAG_TOP_K
        vec_results = self.search_vector(query, top_k * 2)
        bm25_results = self.search_bm25(query, top_k * 2)

        # Reciprocal Rank Fusion
        rrf_scores = defaultdict(float)
        k_constant = 60
        for rank, r in enumerate(vec_results):
            rrf_scores[r["id"]] += 1.0 / (k_constant + rank + 1)
        for rank, r in enumerate(bm25_results):
            rrf_scores[r["id"]] += 1.0 / (k_constant + rank + 1)

        # Merge
        all_docs = {r["id"]: r for r in vec_results + bm25_results}
        ranked = sorted(rrf_scores.items(), key=lambda x: -x[1])

        results = []
        for doc_id, score in ranked[:top_k]:
            doc = all_docs[doc_id]
            doc["score"] = round(score, 4)
            doc["method"] = "hybrid"
            results.append(doc)

        return results

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def doc_count(self) -> int:
        return len(self.documents)


# Global document store instance
doc_store = DocumentStore()


def index_news_from_table_callback(symbol_data: dict):
    """Callback to index a news article from the streaming table."""
    doc_store.add_document(
        title=symbol_data.get("title", ""),
        body=symbol_data.get("body", ""),
        source=symbol_data.get("source", ""),
        published_at=symbol_data.get("published_at", ""),
    )


def retrieve(query: str, top_k: int = None) -> list[dict]:
    """Public retrieval function using hybrid search."""
    return doc_store.hybrid_search(query, top_k)
