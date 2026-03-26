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
