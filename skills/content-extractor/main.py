"""Content Extractor - Main entry point."""

import os
import re
import json
import argparse
from datetime import datetime
from typing import List

from config import load_config, SourceDocument
from handlers.clipboard import ClipboardHandler
from handlers.file_handler import FileHandler
from handlers.url_handler import URLHandler
from extractors.markdown_extractor import MarkdownExtractor
from extractors.image_extractor import ImageExtractor
from extractors.pdf_extractor import PDFExtractor
from extractors.vision_mapper import VisionMapper
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
        self.url_handler = URLHandler()
        self.markdown_extractor = MarkdownExtractor()
        self.image_extractor = ImageExtractor()
        self.pdf_extractor = PDFExtractor()
        self.vision_mapper = VisionMapper()
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
        all_vision_functions = []
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
                    content_type, content_or_path = result
                    if content_type == "markdown":
                        paragraphs = self.markdown_extractor.extract(content_or_path, source=source.path)
                        all_paragraphs.extend(paragraphs.paragraphs)
                    elif content_type == "image":
                        # 完整提取：OCR + Vision 两层信息
                        image_result = self.image_extractor.extract_full(
                            content_or_path,
                            vision_result=getattr(source, 'vision', None)
                        )
                        combined_text = image_result.get("combined_text", "")
                        if combined_text:
                            paragraphs = self.markdown_extractor.extract(combined_text, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                        # 处理 Vision 结果
                        if image_result.get("vision"):
                            last_para_id = paragraphs.paragraphs[-1].id if paragraphs.paragraphs else None
                            all_references.append({
                                "type": "vision_analysis",
                                "target": image_result["vision"].get("page_type", "UI Component"),
                                "confidence": 0.95,
                                "data": image_result["vision"],
                                "source_paragraph": last_para_id
                            })
                            # 转换 Vision 组件为 Function 并加入 structured
                            vision_funcs = self.vision_mapper.vision_to_functions(
                                image_result["vision"],
                                source_id=last_para_id or source.path
                            )
                            all_vision_functions.extend(vision_funcs)

                    elif content_type == "pdf":
                        # PDF 提取：text + embedded images (for OCR/Vision)
                        pdf_result = self.pdf_extractor.extract_full(content_or_path)
                        if pdf_result:
                            # 处理 PDF 文本
                            pdf_text = "\n\n".join(pdf_result.get("pages", []))
                            if pdf_text.strip():
                                paragraphs = self.markdown_extractor.extract(pdf_text, source=source.path)
                                all_paragraphs.extend(paragraphs.paragraphs)
                            # 处理 PDF 内嵌图片 (if any)
                            pdf_images = pdf_result.get("images", [])
                            for page_idx, page_imgs in enumerate(pdf_images):
                                for img_data in page_imgs:
                                    # img_data 可能是图片路径或图片对象
                                    if isinstance(img_data, str) and os.path.exists(img_data):
                                        image_result = self.image_extractor.extract_full(
                                            img_data,
                                            vision_result=getattr(source, 'vision', None)
                                        )
                                        combined_text = image_result.get("combined_text", "")
                                        if combined_text:
                                            img_paragraphs = self.markdown_extractor.extract(
                                                combined_text,
                                                source=f"{source.path}#page={page_idx+1}"
                                            )
                                            all_paragraphs.extend(img_paragraphs)
                                        if image_result.get("vision"):
                                            last_para_id = img_paragraphs[-1].id if img_paragraphs else None
                                            all_references.append({
                                                "type": "vision_analysis",
                                                "target": image_result["vision"].get("page_type", "UI Component"),
                                                "confidence": 0.95,
                                                "data": image_result["vision"],
                                                "source_paragraph": last_para_id
                                            })
                                            # 转换 Vision 组件为 Function 并加入 structured
                                            vision_funcs = self.vision_mapper.vision_to_functions(
                                                image_result["vision"],
                                                source_id=last_para_id or f"{source.path}#page={page_idx+1}"
                                            )
                                            all_vision_functions.extend(vision_funcs)
                                        # Cleanup temp image file
                                        try:
                                            os.unlink(img_data)
                                        except Exception:
                                            pass
                    all_sources.append(f"file:{source.path}")

            elif source.type == "url":
                if not self.url_handler.can_handle(source.path):
                    all_sources.append(f"url:{source.path} (unsupported)")
                else:
                    fetch_result = self.url_handler.fetch(source.path)
                    if fetch_result:
                        content_type, content_or_path = fetch_result
                        if content_type == "text":
                            paragraphs = self.markdown_extractor.extract(content_or_path, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                        elif content_type == "markdown":
                            paragraphs = self.markdown_extractor.extract(content_or_path, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                        elif content_type == "html":
                            # Strip HTML tags for text extraction
                            import re
                            text = re.sub(r'<[^>]+>', '', content_or_path)
                            paragraphs = self.markdown_extractor.extract(text, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                        elif content_type == "image":
                            image_result = self.image_extractor.extract_full(
                                content_or_path,
                                vision_result=getattr(source, 'vision', None)
                            )
                            if image_result.get("combined_text"):
                                img_paragraphs = self.markdown_extractor.extract(
                                    image_result["combined_text"],
                                    source=source.path
                                )
                                all_paragraphs.extend(img_paragraphs)
                            if image_result.get("vision"):
                                last_para_id = img_paragraphs[-1].id if img_paragraphs else None
                                all_references.append({
                                    "type": "vision_analysis",
                                    "target": image_result["vision"].get("page_type", "UI Component"),
                                    "confidence": 0.95,
                                    "data": image_result["vision"],
                                    "source_paragraph": last_para_id
                                })
                                # 转换 Vision 组件为 Function 并加入 structured
                                vision_funcs = self.vision_mapper.vision_to_functions(
                                    image_result["vision"],
                                    source_id=last_para_id or source.path
                                )
                                all_vision_functions.extend(vision_funcs)
                            # Cleanup temp image file
                            self.url_handler.cleanup_temp_file(content_or_path)
                        elif content_type == "pdf":
                            pdf_result = self.pdf_extractor.extract_full(content_or_path)
                            if pdf_result:
                                pdf_text = "\n\n".join(pdf_result.get("pages", []))
                                if pdf_text.strip():
                                    paragraphs = self.markdown_extractor.extract(pdf_text, source=source.path)
                                    all_paragraphs.extend(paragraphs.paragraphs)
                                # Process embedded images
                                for page_idx, page_imgs in enumerate(pdf_result.get("images", [])):
                                    for img_data in page_imgs:
                                        if isinstance(img_data, str) and os.path.exists(img_data):
                                            img_result = self.image_extractor.extract_full(img_data)
                                            if img_result.get("combined_text"):
                                                img_paragraphs = self.markdown_extractor.extract(
                                                    img_result["combined_text"],
                                                    source=f"{source.path}#page={page_idx+1}"
                                                )
                                                all_paragraphs.extend(img_paragraphs)
                                            if img_result.get("vision"):
                                                last_para_id = img_paragraphs[-1].id if img_paragraphs else None
                                                all_references.append({
                                                    "type": "vision_analysis",
                                                    "target": img_result["vision"].get("page_type", "UI Component"),
                                                    "confidence": 0.95,
                                                    "data": img_result["vision"],
                                                    "source_paragraph": last_para_id
                                                })
                                                # 转换 Vision 组件为 Function
                                                vision_funcs = self.vision_mapper.vision_to_functions(
                                                    img_result["vision"],
                                                    source_id=last_para_id or f"{source.path}#page={page_idx+1}"
                                                )
                                                all_vision_functions.extend(vision_funcs)
                                            # Cleanup temp image
                                            self.url_handler.cleanup_temp_file(img_data)
                                # Cleanup temp PDF
                                self.url_handler.cleanup_temp_file(content_or_path)
                        all_sources.append(f"url:{source.path}")
                    else:
                        all_sources.append(f"url:{source.path} (fetch failed)")

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

        # Add Vision-derived functions
        structured.functions.extend(all_vision_functions)

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
            all_paragraphs, structured, conflicts, all_sources, all_references
        )

        # Write outputs
        report_path = os.path.join(output_dir, "requirements-report.md")
        json_path = os.path.join(output_dir, "requirements-report.json")
        graph_path = os.path.join(output_dir, "requirements-graph.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_output)

        # Write graph output
        graph_data = self.graph_builder.to_dict()
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

        return {
            "report_path": report_path,
            "json_path": json_path,
            "graph_path": graph_path,
            "stats": {
                "paragraphs": len(all_paragraphs),
                "functions": len(structured.functions),
                "vision_functions": len(all_vision_functions),
                "conflicts": len(conflicts),
                "references": len(all_references)
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
