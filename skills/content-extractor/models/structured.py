"""L2: Structured Model - machine readable."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .paragraph import Paragraph


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

    # Domain classification
    domain: Optional[str] = None

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

    def merge_duplicates(self, aligner, threshold: float = 0.85):
        """
        Merge functions that refer to the same entity using EntityAligner.

        Finds groups of functions with similar names (across Chinese/English
        variations), then merges them by combining source_paragraphs into the
        first function and removing the duplicates.

        Args:
            aligner: EntityAligner instance
            threshold: similarity threshold for merge (0.85 = high confidence)
        """
        # Build entity dicts for EntityAligner
        entities = [
            {
                "id": f.id,
                "name": f.name,
                "name_normalized": f.name_normalized,
            }
            for f in self.functions
        ]

        # Find merge candidates
        merge_groups = aligner.find_merge_candidates(entities, threshold=threshold)

        if not merge_groups:
            return 0

        # Build a map from function id -> function
        id_to_func = {f.id: f for f in self.functions}

        # For each merge group, keep first, absorb others
        ids_to_remove = set()
        for group in merge_groups:
            primary = group[0]
            primary_func = id_to_func.get(primary["id"])
            if not primary_func:
                continue

            for duplicate in group[1:]:
                dup_func = id_to_func.get(duplicate["id"])
                if not dup_func:
                    continue

                # Absorb source_paragraphs
                for sp in dup_func.source_paragraphs:
                    if sp not in primary_func.source_paragraphs:
                        primary_func.source_paragraphs.append(sp)

                # Absorb cross_references
                for ref in dup_func.cross_references:
                    if ref not in primary_func.cross_references:
                        primary_func.cross_references.append(ref)

                # Merge attributes (prefer non-empty)
                for k, v in dup_func.attributes.items():
                    if k not in primary_func.attributes:
                        primary_func.attributes[k] = v

                ids_to_remove.add(dup_func.id)

        # Remove duplicate functions
        if ids_to_remove:
            self.functions = [f for f in self.functions if f.id not in ids_to_remove]

        return len(ids_to_remove)


@dataclass
class ExtractedData:
    """Complete extraction result."""
    l1_paragraphs: List["Paragraph"] = field(default_factory=list)
    l2_structured: StructuredData = field(default_factory=StructuredData)

    # Cross-document relations
    cross_doc_relations: List[Dict] = field(default_factory=list)

    # Conflicts
    conflicts: List[Dict] = field(default_factory=list)

    # Metadata
    sources: List[str] = field(default_factory=list)
    extracted_at: str = ""
