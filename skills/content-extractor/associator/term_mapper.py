"""Term-based association using dictionary lookup."""

from typing import List, Set, Tuple, Optional
from models.structured import Function
from dictionaries import TermDictionary


class TermMapper:
    """Maps terms between documents using dictionary lookup."""

    def __init__(self, dictionary: TermDictionary = None):
        self.dictionary = dictionary or TermDictionary()

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector using sentence-transformers (if available)."""
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, '_embedding_model'):
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = self._embedding_model.encode([text])[0]
            return embedding.tolist()
        except ImportError:
            return None

    def extract_terms(self, text: str) -> Set[str]:
        """Extract all matching terms from text."""
        return self.dictionary.find_matching_terms(text)

    def find_associations(
        self,
        source_terms: Set[str],
        target_candidates: List[Function]
    ) -> List[Tuple[Function, float]]:
        """
        Find associations based on term overlap.

        Returns:
            List of (function, confidence) tuples
        """
        associations = []

        for func in target_candidates:
            score = self._calculate_term_overlap(source_terms, func)
            if score > 0:
                associations.append((func, score))

        # Sort by score descending
        associations.sort(key=lambda x: x[1], reverse=True)
        return associations

    def _calculate_term_overlap(self, source_terms: Set[str], func: Function) -> float:
        """Calculate term overlap score between source and function."""
        if not source_terms:
            return 0.0

        # Get terms from function name
        func_terms = self.extract_terms(func.name)
        func_terms.update(self.extract_terms(func.name_normalized))

        # Get terms from extracted fields
        for field_value in [func.trigger, func.condition, func.action, func.benefit]:
            if field_value:
                func_terms.update(self.extract_terms(field_value))

        if not func_terms:
            return 0.0

        # Jaccard similarity
        intersection = source_terms & func_terms
        union = source_terms | func_terms

        return len(intersection) / len(union) if union else 0.0

    def build_term_normalized(self, text: str) -> str:
        """Build normalized term from text using dictionary."""
        terms = self.extract_terms(text)
        if terms:
            return "_".join(sorted(terms))
        return text.lower().replace(" ", "_")
