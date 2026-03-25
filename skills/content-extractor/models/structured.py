"""L2: Structured Model - machine readable."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Function:
    id: str
    name: str
    name_normalized: str  # e.g., "user_login"
    source_paragraphs: List[str] = field(default_factory=list)

    # Extracted fields
    trigger: Optional[str] = None
    condition: Optional[str] = None
    action: Optional[str] = None
    benefit: Optional[str] = None

    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    priority_from_source: Optional[str] = None
    source_authority: Optional[str] = None

    # Associations
    cross_references: List[Dict] = field(default_factory=list)

    # Confidence & conflicts
    confidence: float = 1.0
    conflicts: List[Dict] = field(default_factory=list)
    needs_review: bool = False


@dataclass
class StructuredData:
    functions: List[Function] = field(default_factory=list)
    business_rules: List[Dict] = field(default_factory=list)
    data_contracts: List[Dict] = field(default_factory=list)

    def add_function(self, func: Function):
        self.functions.append(func)

    def get_function(self, func_id: str) -> Optional[Function]:
        for f in self.functions:
            if f.id == func_id:
                return f
        return None


@dataclass
class ExtractedData:
    """Complete extraction result."""
    l1_paragraphs: List[Paragraph] = field(default_factory=list)
    l2_structured: StructuredData = field(default_factory=StructuredData)

    # Cross-document relations
    cross_doc_relations: List[Dict] = field(default_factory=list)

    # Conflicts
    conflicts: List[Dict] = field(default_factory=list)

    # Metadata
    sources: List[str] = field(default_factory=list)
    extracted_at: str = ""
