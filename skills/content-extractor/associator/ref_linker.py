"""Cross-document reference extraction and linking."""

import re
from typing import List, Dict, Tuple, Optional


class RefLinker:
    """Extracts and resolves cross-document references."""

    # Reference patterns
    CROSS_DOC_PATTERNS = [
        # Original patterns
        r"详见[\u300a\"]?(.+?)[\u300b\u6587\u6863\u624b\u518c]",
        r"参见[\u300a\"]?(.+?)[\u300b\]]",
        r"[\u300a\"]?(.+?)[\u300b\]]\s*[\u7b2c\u89c1]?\s*([0-9.]+)[\u7ae0]?",
        # New implicit reference patterns
        r"如上所述",  # as mentioned above
        r"如前所述",  # as previously described
        r"前述",  # aforementioned
        r"同上述([A-Za-z0-9_\u4e00-\u9fa5]+)",  # same as above X
        r"同下述([A-Za-z0-9_\u4e00-\u9fa5]+)",  # same as below X
        r"同前述([A-Za-z0-9_\u4e00-\u9fa5]+)",  # same as aforementioned X
        r"参见([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # plain "参见X" without brackets
        r"依据([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # according to X
        r"按照([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # based on X
        r"符合([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # conforms to X
        r"满足([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # satisfies X
        r"参照([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # reference X
        r"根据([A-Za-z0-9_\u4e00-\u9fa5-]+)",  # based on X
        r"RFC-?(\d+)",  # RFC references (RFC12 or RFC-12)
    ]

    SECTION_PATTERNS = [
        r"见第?([0-9.]+)节?",
        r"如图?([0-9]+(?:\.[0-9]+)?)",
        r"参考第?([0-9.]+)节",
        r"第([一二三四五六七八九十零]+)章"
    ]

    CN_DIGIT_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "零": 0}

    URL_PATTERN = r"https?://[^\s<>\"]+"

    # Implicit sequential reference patterns (no capture group needed)
    SEQUENTIAL_PATTERNS = [
        r"之后",  # after
        r"随后",  # subsequently
        r"接下来",  # next
    ]

    # Patterns that indicate implicit back-references (pure self-references without targets)
    BACK_REFERENCE_PATTERNS = [
        "如上所述",
        "如前所述",
        "前述",
    ]

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
                # Handle patterns with or without capture groups
                target = match.group(1).strip() if match.lastindex and match.group(1) else match.group(0).strip()
                ref_type = "implicit" if target in self.BACK_REFERENCE_PATTERNS else "cross_doc"
                references.append({
                    "type": ref_type,
                    "target": target,
                    "confidence": 0.95 if ref_type == "cross_doc" else 0.7,
                    "match": match.group(0)
                })

        # Sequential references (implicit)
        for pattern in self.SEQUENTIAL_PATTERNS:
            for match in re.finditer(pattern, text):
                references.append({
                    "type": "sequential",
                    "target": "implicit_next",
                    "confidence": 0.6,
                    "match": match.group(0)
                })

        # Section references
        for pattern in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                section = match.group(1)
                # Convert Chinese numerals to Arabic for section numbers
                if re.match(r"^[一二三四五六七八九十零]+$", section):
                    section_num = 0
                    if "十" in section:
                        parts = section.split("十")
                        if parts[0] == "":
                            section_num = 10
                        else:
                            section_num = self.CN_DIGIT_MAP.get(parts[0], 0) * 10
                        if len(parts) > 1 and parts[1]:
                            section_num += self.CN_DIGIT_MAP.get(parts[1], 0)
                    else:
                        section_num = self.CN_DIGIT_MAP.get(section, 0)
                    target = f"section_{section_num}"
                else:
                    target = f"section_{section}"
                references.append({
                    "type": "section",
                    "target": target,
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

    def resolve_implicit_reference(
        self,
        ref: Dict,
        known_entities: Dict[str, List[str]],
        context: Optional[Dict] = None
    ) -> Tuple[Optional[str], float]:
        """
        Resolve implicit reference to entity ID with confidence score.

        Args:
            ref: Reference dict with type and target
            known_entities: Dict[entity_name, entity_ids]
            context: Optional context with 'previous_entity' for back-references

        Returns:
            Tuple of (resolved_entity_id, confidence_score)
        """
        target = ref.get("target", "")
        ref_type = ref.get("type", "")
        confidence = ref.get("confidence", 0.5)

        # Handle back-reference patterns (如上所述, 如前所述, etc.)
        if target in self.BACK_REFERENCE_PATTERNS:
            # Use context's previous_entity if available
            if context and "previous_entity" in context:
                prev = context["previous_entity"]
                if prev in known_entities:
                    return known_entities[prev][0], 0.85
            # Otherwise, find the most recently mentioned entity
            # Return the first entity as fallback (most recent in ordered dict)
            if known_entities:
                first_key = next(iter(known_entities))
                return known_entities[first_key][0], 0.6
            return None, 0.0

        # Handle RFC references (RFC12 or RFC-12)
        rfc_match = re.match(r"RFC-?(\d+)", target, re.IGNORECASE)
        if rfc_match:
            rfc_num = rfc_match.group(1)
            # Look for entities with "RFC X", "RFC-X", "rfc_x" pattern (case-insensitive)
            for name, ids in known_entities.items():
                name_lower = name.lower()
                if f"rfc_{rfc_num}" in name_lower or f"rfc {rfc_num}" in name_lower or f"rfc-{rfc_num}" in name_lower:
                    return ids[0], 0.9
            return None, 0.0

        # Handle "同X" type references (同配置, 同文档, etc.)
        if target.startswith("同") and len(target) > 1:
            suffix = target[1:]  # Get the part after "同"
            # Fuzzy match against known entities
            best_match = None
            best_score = 0.0
            for name, ids in known_entities.items():
                # Check if suffix matches any part of the entity name
                if suffix in name:
                    score = len(suffix) / max(len(name), 1)
                    if score > best_score:
                        best_score = score
                        best_match = ids[0]
            if best_match:
                return best_match, min(0.5 + best_score * 0.4, 0.85)
            return None, 0.0

        # Handle sequential references (implicit_next)
        if ref_type == "sequential" and target == "implicit_next":
            if context and "next_entity" in context:
                next_ent = context["next_entity"]
                if next_ent in known_entities:
                    return known_entities[next_ent][0], 0.8
            # Fallback: return second entity if available
            if len(known_entities) > 1:
                keys = list(known_entities.keys())
                return known_entities[keys[1]][0], 0.5
            return None, 0.0

        # For other implicit references, try fuzzy match
        if ref_type == "implicit":
            target_lower = target.lower()
            for name, ids in known_entities.items():
                if target_lower in name.lower() or name.lower() in target_lower:
                    return ids[0], 0.7

        return None, confidence
