"""Full-text search index for Functions using MeiliSearch."""

from typing import List, Dict, Any, Optional
import json


try:
    import meilisearch
    MEILI_AVAILABLE = True
except ImportError:
    MEILI_AVAILABLE = False
    meilisearch = None


class FullTextIndex:
    """MeiliSearch-based full-text index for Function search.

    Falls back to simple in-memory search if MeiliSearch is not available.
    """

    def __init__(self, url: str = "http://localhost:7700", api_key: str = None):
        self.url = url
        self.api_key = api_key
        self.client = None
        self.index = None
        self._functions: Dict[str, dict] = {}  # Fallback in-memory store
        self._use_memory = True
        if MEILI_AVAILABLE:
            try:
                self.client = meilisearch.Client(url, api_key)
                self.index = self.client.index("functions")
                self._use_memory = False
            except Exception:
                pass

    def add_function(self, func_id: str, name: str, metadata: Dict[str, Any]) -> None:
        doc = {"id": func_id, "name": name, **metadata}
        if self._use_memory:
            self._functions[func_id] = doc
        else:
            self.index.add_documents([doc], primary_key="id")

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if self._use_memory:
            return self._memory_search(query, top_k)
        try:
            results = self.index.search(query, {"limit": top_k})
            return results["hits"]
        except Exception:
            return self._memory_search(query, top_k)

    def _memory_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Simple in-memory fallback search."""
        query_lower = query.lower()
        scored = []
        for func_id, doc in self._functions.items():
            text = f"{doc.get('name', '')} {doc.get('trigger', '')} {doc.get('action', '')}".lower()
            if query_lower in text:
                score = text.count(query_lower)
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:top_k]]

    def clear(self) -> None:
        if self._use_memory:
            self._functions.clear()
        else:
            self.index.delete_all_documents()


class FullTextSearcher:
    """High-level search API that combines Function search with domain filtering."""

    def __init__(self, index: FullTextIndex):
        self.index = index

    def search(self, query: str, domain: str = None, top_k: int = 10) -> List[Dict[str, Any]]:
        results = self.index.search(query, top_k * 2)  # Over-fetch for filtering
        if domain:
            results = [r for r in results if r.get("domain") == domain]
        return results[:top_k]
