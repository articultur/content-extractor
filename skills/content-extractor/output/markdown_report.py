"""Generate Markdown report from extracted data."""

from typing import List
from datetime import datetime
from models.paragraph import Paragraph
from models.structured import Function, StructuredData
from merger.conflict_resolver import Conflict


class MarkdownReportGenerator:
    """Generates Markdown reports."""

    def generate(
        self,
        paragraphs: List[Paragraph],
        structured: StructuredData,
        conflicts: List[Conflict],
        sources: List[str]
    ) -> str:
        """Generate complete Markdown report."""
        lines = []

        # Header
        lines.append("# Requirements Analysis Report")
        lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        # Sources
        lines.append("## Sources")
        for source in sources:
            lines.append(f"- {source}")
        lines.append("")

        # Functions
        lines.append("## Extracted Functions")
        for func in structured.functions:
            lines.append(f"\n### {func.name}")
            lines.append(f"- ID: `{func.id}`")
            lines.append(f"- Normalized: `{func.name_normalized}`")

            if func.trigger:
                lines.append(f"- **Trigger**: {func.trigger}")
            if func.condition:
                lines.append(f"- **Condition**: {func.condition}")
            if func.action:
                lines.append(f"- **Action**: {func.action}")
            if func.benefit:
                lines.append(f"- **Benefit**: {func.benefit}")

            lines.append(f"- Confidence: {func.confidence:.2f}")

            if func.source_paragraphs:
                lines.append(f"- Source: {', '.join(func.source_paragraphs)}")

        # Conflicts section
        unresolved = [c for c in conflicts if not c.resolved]
        if unresolved:
            lines.append("\n## Pending Review Items")
            lines.append(f"\n*Found {len(unresolved)} items needing review*\n")

            for i, conflict in enumerate(unresolved, 1):
                lines.append(f"\n### {i}. [{conflict.id}] {conflict.field} - {conflict.severity.upper()}")
                lines.append(f"\n**Severity**: {conflict.severity}")
                lines.append("\n**Conflicting Values:**")
                for val in conflict.values:
                    lines.append(f"- {val['source']}: \"{val['content']}\" (authority: {val.get('authority', 'unknown')})")

                lines.append(f"\n**Suggestion**: {conflict.values[0]['content'] if conflict.values else 'Review required'}")

        lines.append("\n---\n")
        lines.append("*End of Report*")

        return "\n".join(lines)
