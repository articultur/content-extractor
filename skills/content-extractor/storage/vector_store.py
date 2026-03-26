"""Vector store abstraction for semantic search."""

from typing import List, Protocol, Dict
from dataclasses import dataclass


@dataclass
class SearchResult:
    id: str
    score: float
    text: str


class VectorStore(Protocol):
    """Protocol defining the vector store interface."""

    def add(self, id: str, text: str, metadata: dict = None) -> None: ...
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]: ...
    def delete(self, id: str) -> None: ...
    def clear(self) -> None: ...


class InMemoryVectorStore:
    """Fallback when chromadb is not available. Uses TF-IDF cosine similarity."""

    def __init__(self):
        self.vectors: Dict[str, tuple] = {}
        self._all_words: set = set()  # Global vocabulary for consistent encoding

    def add(self, id: str, text: str, metadata: dict = None) -> None:
        words = self._get_words(text)
        self._all_words.update(words)
        embedding = self._encode_with_vocab(text, words)
        self.vectors[id] = (text, embedding)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        query_emb = self._encode_with_vocab(query, self._get_words(query))
        scores = []
        for vid, (text, emb) in self.vectors.items():
            score = self._cosine(query_emb, emb)
            scores.append((vid, score, text))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [SearchResult(id=v[0], score=v[1], text=v[2]) for v in scores[:top_k]]

    def _get_words(self, text: str) -> set:
        """Extract words from text as a set."""
        text_lower = text.lower()
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return set(list(text_lower))
        return set(text_lower.split())

    def _encode_with_vocab(self, text: str, words: set) -> list:
        """Encode text using the global vocabulary."""
        if not self._all_words:
            return [0]  # Empty vocabulary case
        return [1 if w in words else 0 for w in sorted(self._all_words)]

    def _cosine(self, a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-10)

    def delete(self, id: str) -> None:
        self.vectors.pop(id, None)

    def clear(self) -> None:
        self.vectors.clear()
        self._all_words.clear()


try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    chromadb = None


class ChromaVectorStore:
    """ChromaDB-based vector store with sentence-transformers embeddings."""

    def __init__(self, collection_name: str = "functions", embedding_model: str = "all-MiniLM-L6-v2"):
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb not installed: pip install chromadb sentence-transformers")
        self.client = chromadb.Client(Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.embedding_model = embedding_model
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.embedding_model)
        return self._model

    def add(self, id: str, text: str, metadata: dict = None) -> None:
        embedding = self._get_model().encode([text])[0]
        self.collection.add(ids=[id], embeddings=[embedding.tolist()], documents=[text], metadatas=[metadata or {}])

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        query_embedding = self._get_model().encode([query])[0]
        results = self.collection.query(query_embeddings=[query_embedding.tolist()], n_results=top_k)
        return [SearchResult(id=results["ids"][0][i], score=float(results["distances"][0][i]), text=results["documents"][0][i]) for i in range(len(results["ids"][0]))]

    def delete(self, id: str) -> None:
        self.collection.delete(ids=[id])

    def clear(self) -> None:
        self.collection.delete(where={})


def create_vector_store(backend: str = "auto") -> VectorStore:
    """Factory function to create a vector store instance."""
    if backend == "chroma" and CHROMA_AVAILABLE:
        return ChromaVectorStore()
    elif backend == "inmemory":
        return InMemoryVectorStore()
    elif backend == "auto":
        if CHROMA_AVAILABLE:
            return ChromaVectorStore()
        return InMemoryVectorStore()
    else:
        raise ValueError(f"Unknown backend: {backend}")