"""Detect and resolve conflicts between extracted data."""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Conflict:
    id: str
    type: str  # field_value, missing_field, etc.
    severity: str  # high, medium, low
    field: str
    values: List[Dict]  # [{"source": ..., "content": ..., "authority": ...}]
    resolved: bool = False
    final_value: Optional[str] = None
    needs_human: bool = False


class ConflictResolver:
    """Detects and resolves conflicts in extracted data."""

    # Decision authority priority
    AUTHORITY_PRIORITY = {
        "甲方": 5,
        "产品经理": 4,
        "需求文档": 4,
        "开发": 3,
        "测试": 2,
        "LLM": 1,
        "unknown": 0
    }

    def detect_conflicts(self, functions: List) -> List[Conflict]:
        """Detect conflicts between functions."""
        conflicts = []
        conflict_id = 1

        # Compare functions with same normalized name
        func_map = {}
        for func in functions:
            key = func.name_normalized
            if key not in func_map:
                func_map[key] = []
            func_map[key].append(func)

        # Check for conflicts
        for key, funcs in func_map.items():
            if len(funcs) < 2:
                continue

            # Check attribute conflicts
            for i in range(len(funcs)):
                for j in range(i + 1, len(funcs)):
                    conflict = self._compare_functions(funcs[i], funcs[j], conflict_id)
                    if conflict:
                        conflicts.append(conflict)
                        conflict_id += 1

        return conflicts

    def _compare_functions(self, func1, func2, conflict_id: int) -> Optional[Conflict]:
        """Compare two functions for conflicts."""
        # Compare conditions
        if func1.condition and func2.condition:
            if func1.condition != func2.condition:
                return Conflict(
                    id=f"conflict_{conflict_id:03d}",
                    type="field_value",
                    severity="medium",
                    field="condition",
                    values=[
                        {"source": func1.source_paragraphs[0] if func1.source_paragraphs else "unknown",
                         "content": func1.condition,
                         "authority": func1.source_authority or "unknown"},
                        {"source": func2.source_paragraphs[0] if func2.source_paragraphs else "unknown",
                         "content": func2.condition,
                         "authority": func2.source_authority or "unknown"}
                    ],
                    needs_human=True
                )
        return None

    def resolve_by_authority(self, conflict: Conflict) -> str:
        """Resolve conflict using authority priority."""
        if not conflict.values:
            return None

        # Sort by authority
        sorted_values = sorted(
            conflict.values,
            key=lambda v: self.AUTHORITY_PRIORITY.get(v.get("authority", "unknown"), 0),
            reverse=True
        )

        return sorted_values[0]["content"] if sorted_values else None

    def mark_for_human_review(self, conflict: Conflict, suggestion: str):
        """Mark conflict for human review."""
        conflict.needs_human = True
        conflict.resolved = False

    def apply_resolution(self, conflict: Conflict, value: str):
        """Apply human resolution."""
        conflict.final_value = value
        conflict.resolved = True
        conflict.needs_human = False
