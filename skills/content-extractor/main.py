"""Content Extractor - Main entry point."""

import os
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict

from config import load_config, SourceDocument
from handlers.clipboard import ClipboardHandler
from handlers.file_handler import FileHandler
from handlers.url_handler import URLHandler
from extractors.markdown_extractor import MarkdownExtractor
from extractors.image_extractor import ImageExtractor
from extractors.pdf_extractor import PDFExtractor
from extractors.docx_extractor import DOCXExtractor
from extractors.vision_mapper import VisionMapper
from associator.term_mapper import TermMapper
from associator.ref_linker import RefLinker
from associator.entity_aligner import EntityAligner
from associator.domain_classifier import DomainClassifier
from merger.conflict_resolver import ConflictResolver
from merger.graph_builder import GraphBuilder
from merger.confidence_calculator import ConfidenceCalculator
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
        self.docx_extractor = DOCXExtractor()
        self.vision_mapper = VisionMapper()
        self.term_mapper = TermMapper()
        self.ref_linker = RefLinker()
        self.entity_aligner = EntityAligner()
        self.domain_classifier = DomainClassifier()
        self.conflict_resolver = ConflictResolver()
        self.graph_builder = GraphBuilder()
        self.confidence_calculator = ConfidenceCalculator()
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
                parsed = self.clipboard_handler.parse(source.content)
                if not parsed:
                    all_sources.append("clipboard:empty")
                else:
                    content_type, content = parsed[0]
                    paragraphs = self.markdown_extractor.extract(content, source="clipboard")
                    all_paragraphs.extend(paragraphs.paragraphs)
                    all_sources.append(f"clipboard:{content_type}")

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
                        paragraphs = None
                        combined_text = image_result.get("combined_text", "")
                        if combined_text:
                            paragraphs = self.markdown_extractor.extract(combined_text, source=source.path)
                            all_paragraphs.extend(paragraphs.paragraphs)
                        # 处理 Vision 结果（即使 OCR 失败，Vision 仍可能有内容）
                        if image_result.get("vision"):
                            last_para_id = paragraphs.paragraphs[-1].id if paragraphs and paragraphs.paragraphs else None
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
                                        img_paragraphs = None
                                        if combined_text:
                                            img_paragraphs = self.markdown_extractor.extract(
                                                combined_text,
                                                source=f"{source.path}#page={page_idx+1}"
                                            )
                                            all_paragraphs.extend(img_paragraphs)
                                        if image_result.get("vision"):
                                            last_para_id = img_paragraphs.paragraphs[-1].id if img_paragraphs and img_paragraphs.paragraphs else None
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

                    elif content_type == "docx":
                        # DOCX 提取：段落文本 + 表格
                        if not self.docx_extractor.is_available():
                            # python-docx 未安装时记录但不处理
                            pass
                        else:
                            docx_result = self.docx_extractor.extract_full(content_or_path)
                            if docx_result:
                                docx_text = docx_result.get("text", "")
                                if docx_text.strip():
                                    paragraphs = self.markdown_extractor.extract(docx_text, source=source.path)
                                    all_paragraphs.extend(paragraphs.paragraphs)
                                # 处理 DOCX 表格（转为文本行）
                                for table_text in docx_result.get("tables", []):
                                    if table_text.strip():
                                        table_paragraphs = self.markdown_extractor.extract(table_text, source=f"{source.path}#table")
                                        all_paragraphs.extend(table_paragraphs.paragraphs)

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
                            img_paragraphs = None
                            if image_result.get("combined_text"):
                                img_paragraphs = self.markdown_extractor.extract(
                                    image_result["combined_text"],
                                    source=source.path
                                )
                                all_paragraphs.extend(img_paragraphs)
                            if image_result.get("vision"):
                                last_para_id = img_paragraphs.paragraphs[-1].id if img_paragraphs and img_paragraphs.paragraphs else None
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
                                            img_paragraphs = None
                                            if img_result.get("combined_text"):
                                                img_paragraphs = self.markdown_extractor.extract(
                                                    img_result["combined_text"],
                                                    source=f"{source.path}#page={page_idx+1}"
                                                )
                                                all_paragraphs.extend(img_paragraphs)
                                            if img_result.get("vision"):
                                                last_para_id = img_paragraphs.paragraphs[-1].id if img_paragraphs and img_paragraphs.paragraphs else None
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

        # Extract cross-references from all collected paragraphs
        for para in all_paragraphs:
            refs = self.ref_linker.extract_references(para.raw_text)
            for ref in refs:
                ref["source_paragraph"] = para.id
            all_references.extend(refs)

        # Build structured data
        structured = StructuredData()
        for i, para in enumerate(all_paragraphs):
            # Extract source type hint from paragraph source path
            source_hint = self._extract_source_hint(para.source)
            confidence = self.confidence_calculator.calculate_paragraph_confidence(
                para, source_hint
            )
            func = Function(
                id=f"func_{i+1:03d}",
                name=para.section or f"Block {i+1}",
                name_normalized=self.term_mapper.build_term_normalized(para.raw_text),
                source_paragraphs=[para.id],
                trigger=self._extract_field(para.sentences, "trigger"),
                condition=self._extract_field(para.sentences, "condition"),
                action=self._extract_field(para.sentences, "action"),
                benefit=self._extract_field(para.sentences, "result"),
                confidence=confidence
            )
            structured.add_function(func)

        # Add Vision-derived functions
        structured.functions.extend(all_vision_functions)

        # Classify functions into domains
        for func in structured.functions:
            if func.domain is None:
                func.domain = self.domain_classifier.classify(func)

        # Add domain nodes to graph
        domain_functions: Dict[str, List[Function]] = {}
        for func in structured.functions:
            if func.domain:
                domain_functions.setdefault(func.domain, []).append(func)

        for domain_name, funcs in domain_functions.items():
            self.graph_builder.add_domain_node(domain_name, {"function_count": len(funcs)})
            for func in funcs:
                self.graph_builder.link_function_to_domain(func.id, domain_name)

        # Link Vision functions to UI pages (rendered_as edges)
        # Build a map of unique page_type -> ui_id to avoid duplicate UI nodes
        page_type_to_ui_id: Dict[str, str] = {}
        for vf in all_vision_functions:
            page_type = vf.attributes.get("page_type")
            if not page_type:
                continue
            if page_type not in page_type_to_ui_id:
                ui_id = f"ui_{self.term_mapper.build_term_normalized(page_type)}"
                page_type_to_ui_id[page_type] = ui_id
                self.graph_builder.link_function_to_ui(vf.id, ui_id, page_type, confidence=0.7)
            else:
                # Already linked this page_type, just add edge
                ui_id = page_type_to_ui_id[page_type]
                self.graph_builder.add_edge(vf.id, ui_id, "rendered_as", 0.7)

        # Merge duplicate functions using EntityAligner
        merged_count = structured.merge_duplicates(self.entity_aligner, threshold=0.85)

        # Detect and resolve conflicts
        all_conflicts = self.conflict_resolver.detect_conflicts(structured.functions)
        resolved_conflicts, unresolved_conflicts = self.conflict_resolver.resolve_conflicts(all_conflicts)
        conflicts = unresolved_conflicts  # Only pass unresolved to output

        # Resolve cross-references to function IDs
        known_entities = {func.name: [func.id] for func in structured.functions}
        for ref in all_references:
            resolved = self.ref_linker.resolve_reference(ref, known_entities)
            if resolved:
                ref["resolved_to"] = resolved
                # Also link the two functions in the graph
                src_para = ref.get("source_paragraph")
                src_func_id = None
                for func in structured.functions:
                    if src_para in func.source_paragraphs:
                        src_func_id = func.id
                        break
                if src_func_id:
                    self.graph_builder.link_function_to_api(
                        src_func_id, resolved, ref.get("target", ""), ref.get("confidence", 0.9)
                    )

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

    def _extract_source_hint(self, source: str) -> str:
        """Extract source type hint from paragraph source path."""
        if not source:
            return "text"
        # Handle "clipboard" case
        if source == "clipboard":
            return "text"
        # Handle URL-like sources
        if source.startswith("http://") or source.startswith("https://"):
            return "url"
        # Extract file extension
        import os
        base = os.path.splitext(source.split("#")[0])[0]  # Remove fragment
        ext = os.path.splitext(source)[1].lower()
        # Map extension to source type
        ext_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".md": "markdown",
            ".txt": "text",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
        }
        return ext_map.get(ext, "text")


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
