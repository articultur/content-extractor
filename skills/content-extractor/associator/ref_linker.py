"""Cross-document reference extraction and linking."""

import re
from typing import List, Dict, Tuple, Optional


class RefLinker:
    """Extracts and resolves cross-document references."""

    # Reference patterns
    CROSS_DOC_PATTERNS = [
        r"详见[《"]?(.+?)[》文档手册]",
        r"参见[《"]?(.+?)[》\]]",
        r"[《"]?(.+?)[》\]]\s*[第见]?\s*([0-9.]+)章?",
    ]

    SECTION_PATTERNS = [
        r"见第?([0-9.]+)节?",
        r"如图?([0-9]+(?:\.[0-9]+)?)",
        r"参考第?([0-9.]+)节"
    ]

    URL_PATTERN = r"https?://[^\s<>\"]+"

    def extract_references(self, text: str) -> List[Dict]:
        """
        Extract all types of references from text.

        Returns:
            List of reference dicts with type, target, and confidence
        """
        references = []

        # Cross-document references
        for pattern in self.CROSS_DOC_PATTERNS:
            for match in re.finditer(pattern, text):
                references.append({
                    "type": "cross_doc",
                    "target": match.group(1).strip(),
                    "confidence": 0.95,  # High confidence for explicit refs
                    "match": match.group(0)
                })

        # Section references
        for pattern in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                section = match.group(1)
                references.append({
                    "type": "section",
                    "target": f"section_{section}",
                    "confidence": 0.9,
                    "match": match.group(0)
                })

        # URLs
        for match in re.finditer(self.URL_PATTERN, text):
            references.append({
                "type": "url",
                "target": match.group(0),
                "confidence": 0.85,
                "match": match.group(0)
            })

        return references

    def resolve_reference(
        self,
        ref: Dict,
        known_entities: Dict[str, List[str]]
    ) -> Optional[str]:
        """
        Resolve reference to entity ID.

        Args:
            ref: Reference dict
            known_entities: Dict[entity_name, entity_ids]

        Returns:
            Resolved entity ID or None
        """
        target = ref["target"]

        # Direct match
        if target in known_entities:
            return known_entities[target][0]  # Return first match

        # Fuzzy match
        target_lower = target.lower()
        for name, ids in known_entities.items():
            if target_lower in name.lower() or name.lower() in target_lower:
                return ids[0]

        return None
