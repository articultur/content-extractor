"""Confidence calculation based on extraction quality signals."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.paragraph import Paragraph, Sentence
    from models.structured import Function


class ConfidenceCalculator:
    """Calculates confidence scores based on extraction quality signals."""

    # Base confidence by source type
    SOURCE_BASE = {
        "text": 0.95,
        "markdown": 0.95,
        "pdf": 0.90,
        "docx": 0.90,
        "image": 0.85,
        "vision": 0.80,
        "url": 0.90,
    }

    # Source type aliases for flexibility
    SOURCE_ALIASES = {
        "clipboard": "text",
        "file:": "file",
    }

    def calculate_paragraph_confidence(
        self,
        para: "Paragraph",
        source_hint: str = "text"
    ) -> float:
        """
        Calculate confidence for a paragraph → Function conversion.

        Args:
            para: The paragraph to evaluate
            source_hint: Hint about source type (e.g., "pdf", "image", "clipboard")

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with source-based base
        base = self._get_base_confidence(source_hint)

        # Content quality adjustments
        adjustments = []

        # Sentence count signal
        if para.sentences:
            sent_count = len(para.sentences)
            if sent_count >= 2 and sent_count <= 10:
                adjustments.append(0.02)  # Reasonable paragraph length
            elif sent_count > 10:
                adjustments.append(0.01)  # Very long, might be multiple topics
        else:
            adjustments.append(-0.05)  # No sentences extracted

        # Has section header signal
        if para.section:
            adjustments.append(0.03)  # Organized with header

        # Raw text length signal
        text_len = len(para.raw_text) if para.raw_text else 0
        if text_len < 10:
            adjustments.append(-0.05)  # Too short to be meaningful
        elif text_len >= 50:
            adjustments.append(0.02)  # Substantial content

        # Field completeness bonus
        roles = [s.role for s in para.sentences] if para.sentences else []
        field_count = sum(1 for r in roles if r in ("trigger", "condition", "action", "result"))
        if field_count >= 3:
            adjustments.append(0.05)  # Well-structured with multiple roles
        elif field_count == 1:
            adjustments.append(-0.02)  # Minimal structure

        # Sentence role completeness bonus
        unique_roles = set(roles)
        if "trigger" in unique_roles and "action" in unique_roles:
            adjustments.append(0.03)  # Has trigger-action pair
        if "condition" in unique_roles and "action" in unique_roles:
            adjustments.append(0.02)  # Has condition-action pair

        # Apply adjustments
        confidence = base + sum(adjustments)
        return max(0.5, min(0.99, confidence))  # Clamp to [0.5, 0.99]

    def calculate_vision_confidence(
        self,
        page_type: str,
        component_count: int
    ) -> float:
        """
        Calculate confidence for Vision-derived functions.

        Args:
            page_type: Type of page (e.g., "Dashboard", "Form")
            component_count: Number of UI components detected

        Returns:
            Confidence score between 0.0 and 1.0
        """
        base = self.SOURCE_BASE["vision"]

        adjustments = []

        # Page type clarity
        if page_type and page_type not in ("Unknown", "Other"):
            adjustments.append(0.05)
        else:
            adjustments.append(-0.05)

        # Component count signal
        if component_count == 0:
            adjustments.append(-0.10)
        elif component_count > 0 and component_count <= 10:
            adjustments.append(0.03)
        elif component_count > 20:
            adjustments.append(-0.02)  # Might be noisy

        confidence = base + sum(adjustments)
        return max(0.5, min(0.95, confidence))

    def _get_base_confidence(self, source_hint: str) -> float:
        """Get base confidence for a source hint."""
        hint_lower = source_hint.lower()

        # Check direct match
        for key, val in self.SOURCE_BASE.items():
            if key in hint_lower:
                return val

        # Check aliases
        for alias, canonical in self.SOURCE_ALIASES.items():
            if alias in hint_lower:
                return self.SOURCE_BASE.get(canonical, 0.9)

        return 0.9  # Default
