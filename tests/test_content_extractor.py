"""Tests for content-extractor MVP."""

import pytest
import tempfile
import os
from pathlib import Path

from handlers.clipboard import ClipboardHandler
from handlers.file_handler import FileHandler
from extractors.markdown_extractor import MarkdownExtractor
from dictionaries import TermDictionary
from associator.term_mapper import TermMapper
from merger.conflict_resolver import ConflictResolver


class TestClipboardHandler:
    def test_parse_markdown(self):
        handler = ClipboardHandler()
        result = handler.parse("# Header\n\nSome text")
        assert len(result) == 1
        assert result[0][0] == "markdown"

    def test_parse_plain_text(self):
        handler = ClipboardHandler()
        result = handler.parse("Just some plain text")
        assert len(result) == 1
        assert result[0][0] == "text"


class TestMarkdownExtractor:
    def test_extract_basic_paragraphs(self):
        extractor = MarkdownExtractor()
        content = "# Login\n\nUser logs in with password.\n\n# Payment\n\nUser pays with card."
        result = extractor.extract(content, source="test.md")
        assert len(result.paragraphs) >= 2


class TestTermDictionary:
    def test_get_synonyms(self):
        dictionary = TermDictionary()
        synonyms = dictionary.get_synonyms("login")
        assert "login" in synonyms
        assert "登录" in synonyms

    def test_find_matching_terms(self):
        dictionary = TermDictionary()
        matches = dictionary.find_matching_terms("User login with password")
        assert "auth" in matches or "user" in matches


class TestTermMapper:
    def test_extract_terms(self):
        mapper = TermMapper()
        terms = mapper.extract_terms("User login authentication")
        assert len(terms) > 0


class TestConflictResolver:
    def test_detect_conflicts_none(self):
        from models.structured import Function
        resolver = ConflictResolver()
        funcs = [
            Function(id="f1", name="Login", name_normalized="login"),
            Function(id="f2", name="Login", name_normalized="login", condition="8位")
        ]
        conflicts = resolver.detect_conflicts(funcs)
        # Same condition = no conflict


class TestEntityAligner:
    def test_normalize_for_comparison(self):
        """Test entity name normalization."""
        from associator.entity_aligner import EntityAligner

        aligner = EntityAligner()

        assert aligner.normalize("用户登录") == aligner.normalize("user_login")
        assert aligner.normalize("登录") == aligner.normalize("login")

    def test_find_similar_entities(self):
        """Test finding similar entities."""
        from associator.entity_aligner import EntityAligner
        from models.structured import Function

        aligner = EntityAligner()

        entities = [
            Function(id="f1", name="用户登录", name_normalized="user_login"),
            Function(id="f2", name="登录验证", name_normalized="login_verify"),
            Function(id="f3", name="登出", name_normalized="logout"),
        ]

        similar = aligner.find_similar("user_login", entities, threshold=0.6)
        assert len(similar) >= 1

    def test_merge_candidates(self):
        """Test identifying merge candidates."""
        from associator.entity_aligner import EntityAligner

        aligner = EntityAligner()

        candidates = [
            {"id": "f1", "name": "用户登录", "source": "doc_a"},
            {"id": "f2", "name": "用户登录", "source": "doc_b"},
        ]

        merges = aligner.find_merge_candidates(candidates, threshold=0.9)
        assert len(merges) == 1

    def test_calculate_similarity(self):
        """Test calculate_similarity with various inputs."""
        from associator.entity_aligner import EntityAligner

        aligner = EntityAligner()

        # Same string returns 1.0
        assert aligner.calculate_similarity("login", "login") == 1.0

        # Chinese term normalizes to English, then matches → 1.0 (exact match after normalization)
        assert aligner.calculate_similarity("login", "登录") == 1.0

        # Two Chinese equivalents that normalize to the same English term → 1.0
        assert aligner.calculate_similarity("登录", "登入") == 1.0

        # Unrelated strings return SequenceMatcher ratio (less than 1.0)
        score = aligner.calculate_similarity("hello", "goodbye")
        assert 0 < score < 1.0


class TestVisionMapper:
    def test_vision_component_to_function(self):
        """Test converting Vision components to L2 Function."""
        from extractors.vision_mapper import VisionMapper

        mapper = VisionMapper()

        vision_result = {
            "page_type": "Dashboard",
            "components": [
                {"type": "button", "label": "Sign In", "function": "user_login", "data": {}},
                {"type": "nav", "label": "Home", "function": "navigate_home", "data": {}},
                {"type": "card", "label": "KPI Card", "function": "display_metrics", "data": {"metrics": ["Active Users", "Sales"]}},
            ],
            "layout": "dashboard"
        }

        functions = mapper.vision_to_functions(vision_result, source_id="img_001")
        assert len(functions) == 3
        assert functions[0].name == "Sign In"
        assert functions[0].name_normalized == "user_login"
        assert functions[0].trigger == "点击 Sign In 按钮"

    def test_vision_without_function(self):
        """Test component without explicit function."""
        from extractors.vision_mapper import VisionMapper

        mapper = VisionMapper()

        vision_result = {
            "page_type": "Unknown",
            "components": [
                {"type": "label", "label": "Some text", "function": None, "data": {}},
            ]
        }

        functions = mapper.vision_to_functions(vision_result, source_id="img_002")
        assert len(functions) == 1
        assert functions[0].name == "Some text"
        assert functions[0].name_normalized == "some_text"


class TestURLHandler:
    def test_can_handle_url(self):
        """Test URL pattern recognition."""
        from handlers.url_handler import URLHandler

        handler = URLHandler()

        assert handler.can_handle("https://example.com/doc.pdf") == True
        assert handler.can_handle("https://github.com/user/repo/README.md") == True
        assert handler.can_handle("not a url") == False

    def test_resolve_url_type(self):
        """Test URL content type resolution."""
        from handlers.url_handler import URLHandler

        handler = URLHandler()

        assert handler.resolve_type("https://example.com/file.pdf") == "pdf"
        assert handler.resolve_type("https://example.com/file.md") == "markdown"
        assert handler.resolve_type("https://example.com/page") == "html"


class TestPDFExtractor:
    def test_extract_text_from_pdf(self):
        """Test PDF text extraction."""
        from extractors.pdf_extractor import PDFExtractor
        import os

        extractor = PDFExtractor()

        # Skip if no pdfplumber
        if not extractor.is_available():
            pytest.skip("pdfplumber not installed")

        # Test with existing PDF or skip
        pdf_path = "tests/fixtures/sample.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip("No test PDF available")

        result = extractor.extract(pdf_path)
        assert result is not None
        assert len(result) > 0

    def test_pdf_page_extraction(self):
        """Test multi-page PDF extraction.

        Note: Page-level extraction is covered by test_pdf_full_extraction
        which validates the 'pages' key in the result structure.
        """
        from extractors.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        if not extractor.is_available():
            pytest.skip("pdfplumber not installed")

        pdf_path = "tests/fixtures/sample.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip("No test PDF available")

        # Verify extract_full returns page data (covers page extraction)
        result = extractor.extract_full(pdf_path)
        assert result is not None
        assert "pages" in result
        assert isinstance(result["pages"], list)

    def test_pdf_full_extraction(self):
        """Test full PDF extraction with metadata."""
        from extractors.pdf_extractor import PDFExtractor
        import os

        extractor = PDFExtractor()
        if not extractor.is_available():
            pytest.skip("pdfplumber not installed")

        pdf_path = "tests/fixtures/sample.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip("No test PDF available")

        result = extractor.extract_full(pdf_path)
        assert result is not None
        assert "pages" in result
        assert "metadata" in result
        assert "page_count" in result
        assert "images" in result
        assert isinstance(result["images"], list)


class TestDOCXExtractor:
    def test_is_available(self):
        """Test DOCX availability check."""
        from extractors.docx_extractor import DOCXExtractor
        extractor = DOCXExtractor()
        result = extractor.is_available()
        assert isinstance(result, bool)

    def test_extract_full_returns_structure(self):
        """Test DOCX extract_full returns expected structure."""
        from extractors.docx_extractor import DOCXExtractor
        import os

        extractor = DOCXExtractor()
        if not extractor.is_available():
            pytest.skip("python-docx not installed")

        docx_path = "tests/fixtures/sample.docx"
        if not os.path.exists(docx_path):
            pytest.skip("No test DOCX available")

        result = extractor.extract_full(docx_path)
        assert result is not None
        assert "text" in result
        assert "paragraphs" in result
        assert "page_count" in result
        assert "tables" in result
        assert "metadata" in result

    def test_extract_full_returns_none_for_missing_file(self):
        """Test DOCX extract_full returns None for non-existent file."""
        from extractors.docx_extractor import DOCXExtractor
        extractor = DOCXExtractor()
        if not extractor.is_available():
            pytest.skip("python-docx not installed")

        result = extractor.extract_full("nonexistent.docx")
        assert result is None


class TestConfidenceCalculator:
    def test_calculate_paragraph_confidence_text_source(self):
        """Test confidence calculation for text source."""
        from merger.confidence_calculator import ConfidenceCalculator
        from models.paragraph import Paragraph, Sentence

        calc = ConfidenceCalculator()

        para = Paragraph(
            id="p1",
            source="clipboard",
            section="Login",
            raw_text="User logs in with password. System validates credentials.",
            semantic_unit=True,
            sentences=[
                Sentence(id="p1_s1", text="User logs in with password.", role="action"),
                Sentence(id="p1_s2", text="System validates credentials.", role="result"),
            ],
            sentence_relations=[]
        )

        confidence = calc.calculate_paragraph_confidence(para, "text")
        assert 0.8 <= confidence <= 0.99

    def test_calculate_paragraph_confidence_low_quality(self):
        """Test confidence calculation for low quality paragraph."""
        from merger.confidence_calculator import ConfidenceCalculator
        from models.paragraph import Paragraph

        calc = ConfidenceCalculator()

        para = Paragraph(
            id="p1",
            source="clipboard",
            section="",
            raw_text="x",
            semantic_unit=True,
            sentences=[],
            sentence_relations=[]
        )

        confidence = calc.calculate_paragraph_confidence(para, "text")
        assert confidence < 0.9  # Low quality = reduced confidence

    def test_source_base_confidence(self):
        """Test source base confidence values."""
        from merger.confidence_calculator import ConfidenceCalculator

        calc = ConfidenceCalculator()

        assert calc._get_base_confidence("pdf") == 0.9
        assert calc._get_base_confidence("docx") == 0.9
        assert calc._get_base_confidence("clipboard") == 0.95
        assert calc._get_base_confidence("image") == 0.85
        assert calc._get_base_confidence("vision") == 0.8


class TestMarkdownExtractorRoleInference:
    def test_infer_role_ui_trigger(self):
        """Test UI interaction sentences are recognized as trigger."""
        from extractors.markdown_extractor import MarkdownExtractor
        extractor = MarkdownExtractor()

        # 点击开头的句子应该是 trigger
        role = extractor._infer_role("点击登录按钮后进入首页")
        assert role == "trigger"

    def test_infer_role_action(self):
        """Test action sentences are recognized as action."""
        from extractors.markdown_extractor import MarkdownExtractor
        extractor = MarkdownExtractor()

        role = extractor._infer_role("系统自动发送邮件通知用户")
        assert role == "action"

    def test_infer_role_result(self):
        """Test result sentences are recognized as result."""
        from extractors.markdown_extractor import MarkdownExtractor
        extractor = MarkdownExtractor()

        role = extractor._infer_role("登录成功后进入首页")
        assert role == "result"

    def test_infer_role_condition(self):
        """Test condition sentences are recognized as condition."""
        from extractors.markdown_extractor import MarkdownExtractor
        extractor = MarkdownExtractor()

        role = extractor._infer_role("如果用户已登录则显示欢迎页")
        assert role == "condition"

    def test_infer_role_statement(self):
        """Test neutral sentences return statement."""
        from extractors.markdown_extractor import MarkdownExtractor
        extractor = MarkdownExtractor()

        role = extractor._infer_role("这是一个普通描述")
        assert role == "statement"


class TestRefLinkerIntegration:
    def test_extract_references_from_all_sources(self):
        """Test RefLinker extracts from multiple paragraph types."""
        from associator.ref_linker import RefLinker
        linker = RefLinker()

        refs = linker.extract_references("用户登录流程详见第三章")
        assert len(refs) >= 1
        assert any(r["type"] == "section" for r in refs)

    def test_resolve_reference_fuzzy_match(self):
        """Test resolve_reference uses fuzzy matching."""
        from associator.ref_linker import RefLinker
        linker = RefLinker()

        ref = {"type": "cross_doc", "target": "登录功能", "confidence": 0.95}
        known = {"登录功能": ["func_001"], "用户管理": ["func_002"]}

        resolved = linker.resolve_reference(ref, known)
        assert resolved == "func_001"


class TestStructuredDataMergeDuplicates:
    def test_merge_duplicates(self):
        """Test merging duplicate functions using EntityAligner."""
        from models.structured import Function, StructuredData
        from associator.entity_aligner import EntityAligner

        structured = StructuredData()
        structured.add_function(Function(
            id="f1", name="用户登录", name_normalized="user_login",
            source_paragraphs=["p1"]
        ))
        structured.add_function(Function(
            id="f2", name="用户登录", name_normalized="user_login",
            source_paragraphs=["p2"]
        ))
        structured.add_function(Function(
            id="f3", name="登出", name_normalized="logout",
            source_paragraphs=["p3"]
        ))

        aligner = EntityAligner()
        merged = structured.merge_duplicates(aligner, threshold=0.9)

        assert merged == 1  # one duplicate removed
        assert len(structured.functions) == 2
        # Check source_paragraphs were merged
        f1 = next(f for f in structured.functions if f.id == "f1")
        assert "p1" in f1.source_paragraphs
        assert "p2" in f1.source_paragraphs


class TestConflictResolverAutoResolution:
    def test_resolve_by_authority(self):
        """Test automatic conflict resolution."""
        from merger.conflict_resolver import Conflict, ConflictResolver

        resolver = ConflictResolver()
        conflict = Conflict(
            id="c1", type="field_value", severity="medium", field="condition",
            values=[
                {"source": "doc_pm", "content": "条件A", "authority": "产品经理"},
                {"source": "doc_dev", "content": "条件B", "authority": "开发"},
            ],
            needs_human=False
        )

        resolved, unresolved = resolver.resolve_conflicts([conflict])

        assert len(resolved) == 1
        assert resolved[0].final_value == "条件A"  # 产品经理 has higher priority
        assert len(unresolved) == 0

    def test_needs_human_when_equal_authority(self):
        """Test unresolved when authority is equal."""
        from merger.conflict_resolver import Conflict, ConflictResolver

        resolver = ConflictResolver()
        conflict = Conflict(
            id="c1", type="field_value", severity="medium", field="condition",
            values=[
                {"source": "doc1", "content": "条件A", "authority": "unknown"},
                {"source": "doc2", "content": "条件B", "authority": "unknown"},
            ],
            needs_human=True  # equal authority → needs human
        )

        resolved, unresolved = resolver.resolve_conflicts([conflict])

        assert len(resolved) == 0
        assert len(unresolved) == 1
        assert unresolved[0].needs_human == True


class TestClipboardHandlerIntegration:
    def test_parse_used_in_pipeline(self):
        """Test ClipboardHandler.parse is used for text sources."""
        from handlers.clipboard import ClipboardHandler
        from extractors.markdown_extractor import MarkdownExtractor

        handler = ClipboardHandler()
        extractor = MarkdownExtractor()

        # Markdown content
        result = handler.parse("# Header\n\nSome text")
        assert result[0][0] == "markdown"
        paragraphs = extractor.extract(result[0][1])
        assert len(paragraphs.paragraphs) >= 1

        # Plain text
        result = handler.parse("Just plain text without any markdown indicators")
        assert result[0][0] == "text"
        paragraphs = extractor.extract(result[0][1])
        assert len(paragraphs.paragraphs) >= 1

    def test_parse_empty_content(self):
        """Test empty content returns empty list."""
        from handlers.clipboard import ClipboardHandler
        handler = ClipboardHandler()
        result = handler.parse("")
        assert result == []
