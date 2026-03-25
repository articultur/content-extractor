"""Content Extractor - Main entry point."""

import os
import argparse
from datetime import datetime
from typing import List

from config import load_config, SourceDocument
from handlers.clipboard import ClipboardHandler
from handlers.file_handler import FileHandler
from extractors.markdown_extractor import MarkdownExtractor
from extractors.image_extractor import ImageExtractor
from associator.term_mapper import TermMapper
from associator.ref_linker import RefLinker
from merger.conflict_resolver import ConflictResolver
from merger.graph_builder import GraphBuilder
from output.markdown_report import MarkdownReportGenerator
from output.json_exporter import JSONExporter
from dictionaries import TermDictionary
from models.structured import Function, StructuredData


class ContentExtractor:
    """Main content extractor orchestrator."""

    def __init__(self):
        self.clipboard_handler = ClipboardHandler()
        self.file_handler = FileHandler()
        self.markdown_extractor = MarkdownExtractor()
        self.image_extractor = ImageExtractor()
        self.term_mapper = TermMapper()
        self.ref_linker = RefLinker()
        self.conflict_resolver = ConflictResolver()
        self.graph_builder = GraphBuilder()
        self.markdown_gen = MarkdownReportGenerator()
        self.json_exporter = JSONExporter()

    def analyze(
        self,
        sources: List[SourceDocument],
        output_dir: str = "./output"
    ) -> dict:
        """
        Analyze all sources and produce report.

        Returns:
            dict with analysis results
        """
        all_paragraphs = []
        all_functions = []
        all_conflicts = []
        all_sources = []
        all_references = []

        # Process each source
        for source in sources:
            if source.type == "text":
                content = source.content
                paragraphs = self.markdown_extractor.extract(content, source="clipboard")
                all_paragraphs.extend(paragraphs.paragraphs)
                all_sources.append("clipboard:text")

            elif source.type == "file":
                result = self.file_handler.read(source.path)
                if result:
                    content_type, content = result
                    if content_type == "markdown":
                        paragraphs = self.markdown_extractor.extract(content, source=source.path)
                        all_paragraphs.extend(paragraphs.paragraphs)
                    elif content_type == "image":
                        ocr_text = self.image_extractor.extract(content)
                        if ocr_text:
                            paragraphs = self.markdown_extractor.extract(ocr_text, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                    all_sources.append(f"file:{source.path}")

            # Extract cross-references
            for para in paragraphs.paragraphs if 'paragraphs' in locals() else []:
                refs = self.ref_linker.extract_references(para.raw_text)
                for ref in refs:
                    ref["source_paragraph"] = para.id
                all_references.extend(refs)

        # Build structured data
        structured = StructuredData()
        for i, para in enumerate(all_paragraphs):
            func = Function(
                id=f"func_{i+1:03d}",
                name=para.section or f"Block {i+1}",
                name_normalized=self.term_mapper.build_term_normalized(para.raw_text),
                source_paragraphs=[para.id],
                trigger=self._extract_field(para.sentences, "trigger"),
                condition=self._extract_field(para.sentences, "condition"),
                action=self._extract_field(para.sentences, "action"),
                benefit=self._extract_field(para.sentences, "result"),
                confidence=0.9
            )
            structured.add_function(func)

        # Detect conflicts
        conflicts = self.conflict_resolver.detect_conflicts(structured.functions)

        # Build associations using term mapper
        for func in structured.functions:
            terms = self.term_mapper.extract_terms(func.raw_text if hasattr(func, 'raw_text') else func.name)
            associations = self.term_mapper.find_associations(terms, structured.functions)
            for target_func, confidence in associations[:3]:  # Top 3
                if target_func.id != func.id:
                    self.graph_builder.link_function_to_api(
                        func.id, target_func.id, target_func.name, confidence
                    )

        # Generate outputs
        os.makedirs(output_dir, exist_ok=True)

        markdown_report = self.markdown_gen.generate(
            all_paragraphs, structured, conflicts, all_sources
        )

        json_output = self.json_exporter.export(
            all_paragraphs, structured, conflicts, all_sources
        )

        # Write outputs
        report_path = os.path.join(output_dir, "requirements-report.md")
        json_path = os.path.join(output_dir, "requirements-report.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_output)

        return {
            "report_path": report_path,
            "json_path": json_path,
            "stats": {
                "paragraphs": len(all_paragraphs),
                "functions": len(structured.functions),
                "conflicts": len(conflicts)
            }
        }

    def _extract_field(self, sentences, role: str) -> str:
        """Extract field value from sentences by role."""
        for s in sentences:
            if s.role == role:
                return s.text
        return None


def main():
    parser = argparse.ArgumentParser(description="Content Extractor")
    parser.add_argument("--config", default="content-extractor.config.yaml",
                        help="Config file path")
    parser.add_argument("--output", default="./output",
                        help="Output directory")
    parser.add_argument("--text", help="Inline text content")

    args = parser.parse_args()

    # Load config or use inline text
    if args.text:
        sources = [SourceDocument(type="text", content=args.text)]
    else:
        config = load_config(args.config)
        sources = config.sources

    if not sources:
        print("No sources to analyze")
        return

    # Run extraction
    extractor = ContentExtractor()
    result = extractor.analyze(sources, args.output)

    print(f"Analysis complete!")
    print(f"  Report: {result['report_path']}")
    print(f"  JSON: {result['json_path']}")
    print(f"  Paragraphs: {result['stats']['paragraphs']}")
    print(f"  Functions: {result['stats']['functions']}")
    print(f"  Conflicts: {result['stats']['conflicts']}")


if __name__ == "__main__":
    main()
