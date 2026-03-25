"""Configuration management for content-extractor."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml
import os


@dataclass
class SourceDocument:
    type: str  # "text", "file", "url"
    path: Optional[str] = None
    content: Optional[str] = None


@dataclass
class ExtractorConfig:
    sources: List[SourceDocument]
    output_dir: str = "./output"
    confidence_threshold_high: float = 0.8
    confidence_threshold_low: float = 0.5


def load_config(config_path: str = "content-extractor.config.yaml") -> ExtractorConfig:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        return ExtractorConfig(sources=[])

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    sources = []
    for doc in data.get('input', {}).get('documents', []):
        sources.append(SourceDocument(
            type=doc['type'],
            path=doc.get('path'),
            content=doc.get('content')
        ))

    return ExtractorConfig(
        sources=sources,
        output_dir=data.get('output', {}).get('dir', './output')
    )
