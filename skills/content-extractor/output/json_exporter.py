"""Export extracted data as JSON."""

import json
from datetime import datetime
from typing import List, Dict
from models.paragraph import Paragraph
from models.structured import Function, StructuredData
from merger.conflict_resolver import Conflict


class JSONExporter:
    """Exports extracted data as JSON."""

    def export(
        self,
        paragraphs: List[Paragraph],
        structured: StructuredData,
        conflicts: List[Conflict],
        sources: List[str],
        actions: List[Dict] = None
    ) -> str:
        """Export complete data as JSON string."""
        data = {
            "metadata": {
                "module": "content-extractor",
                "version": "1.0.0",
                "sources": sources,
                "extracted_at": datetime.now().isoformat(),
                "stats": {
                    "total_paragraphs": len(paragraphs),
                    "total_functions": len(structured.functions),
                    "conflicts_detected": len(conflicts),
                    "unresolved_conflicts": len([c for c in conflicts if not c.resolved])
                }
            },
            "l1_paragraphs": [
                {
                    "id": p.id,
                    "source": p.source,
                    "section": p.section,
                    "raw_text": p.raw_text,
                    "semantic_unit": p.semantic_unit,
                    "sentences": [
                        {"id": s.id, "text": s.text, "role": s.role}
                        for s in p.sentences
                    ]
                }
                for p in paragraphs
            ],
            "l2_structured": {
                "functions": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "name_normalized": f.name_normalized,
                        "trigger": f.trigger,
                        "condition": f.condition,
                        "action": f.action,
                        "benefit": f.benefit,
                        "attributes": f.attributes,
                        "confidence": f.confidence,
                        "source_paragraphs": f.source_paragraphs,
                        "cross_references": f.cross_references,
                        "needs_review": f.needs_review
                    }
                    for f in structured.functions
                ]
            },
            "conflicts": [
                {
                    "id": c.id,
                    "type": c.type,
                    "severity": c.severity,
                    "field": c.field,
                    "values": c.values,
                    "resolved": c.resolved,
                    "final_value": c.final_value,
                    "needs_human": c.needs_human
                }
                for c in conflicts
            ],
            "actions": actions or []
        }

        return json.dumps(data, ensure_ascii=False, indent=2)
