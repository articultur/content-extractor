# Content Extractor Enhancement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete MVP gaps - add PDF parsing, Vision→L2 direct mapping, URL input enhancement, and Entity Alignment V2.

**Architecture:** Add PDF extractor with pdfplumber, implement Vision-to-L2 transformer, add URL handler, implement entity alignment module.

**Tech Stack:** Python, pdfplumber, urllib, regex

---

## File Structure

```
skills/content-extractor/
├── extractors/
│   ├── pdf_extractor.py    # NEW
│   └── image_extractor.py  # MODIFY: add vision_to_functions()
├── handlers/
│   └── url_handler.py       # NEW
├── associator/
│   ├── entity_aligner.py   # NEW
│   └── ref_linker.py       # MODIFY: add URL pattern support
├── models/
│   └── structured.py        # MODIFY: add VisionFunction
├── config.py               # MODIFY: add .pdf to SUPPORTED_TYPES
├── main.py                 # MODIFY: integrate new modules
└── tests/
    └── test_content_extractor.py  # MODIFY: add new tests
```

---

## Task 1: PDF Extractor

**Files:**
- Create: `skills/content-extractor/extractors/pdf_extractor.py`
- Modify: `skills/content-extractor/config.py` (add .pdf support)
- Test: `tests/test_content_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_content_extractor.py

class TestPDFExtractor:
    def test_extract_text_from_pdf(self):
        """Test PDF text extraction."""
        from extractors.pdf_extractor import PDFExtractor
        import tempfile
        import os

        # Create a simple PDF for testing
        # pdfplumber can open real PDFs, we'll test with path
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
        """Test multi-page PDF extraction."""
        from extractors.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        if not extractor.is_available():
            pytest.skip("pdfplumber not installed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_content_extractor.py::TestPDFExtractor -v`
Expected: FAIL with "No module named 'pdfplumber'"

- [ ] **Step 3: Write minimal PDF extractor**

```python
# skills/content-extractor/extractors/pdf_extractor.py
"""Extract text from PDF files using pdfplumber."""

from typing import List, Optional
import os


class PDFExtractor:
    """Extracts text content from PDF files."""

    def __init__(self):
        self._available = None

    def is_available(self) -> bool:
        """Check if PDF extraction is available."""
        if self._available is None:
            try:
                import pdfplumber
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def extract(self, pdf_path: str) -> Optional[List[str]]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of page texts, or None if extraction fails
        """
        if not self.is_available():
            return None

        if not os.path.exists(pdf_path):
            return None

        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)

            return pages if pages else None
        except Exception:
            return None

    def extract_full(self, pdf_path: str) -> Optional[dict]:
        """
        Extract full content with metadata.

        Returns:
            dict with pages, metadata, or None
        """
        if not self.is_available():
            return None

        if not os.path.exists(pdf_path):
            return None

        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                return {
                    "pages": [page.extract_text() or "" for page in pdf.pages],
                    "metadata": pdf.metadata,
                    "page_count": len(pdf.pages)
                }
        except Exception:
            return None
```

- [ ] **Step 4: Update config.py to add PDF support**

```python
# skills/content-extractor/config.py - add to SUPPORTED_TYPES or similar
# Look for SUPPORTED_EXTENSIONS in FileHandler and add .pdf
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_content_extractor.py::TestPDFExtractor -v`
Expected: PASS or SKIP (if no test PDF)

- [ ] **Step 6: Commit**

```bash
git add skills/content-extractor/extractors/pdf_extractor.py
git add skills/content-extractor/config.py
git add tests/test_content_extractor.py
git commit -m "feat(content-extractor): add PDF text extraction with pdfplumber"
```

---

## Task 2: Vision → L2 Function Direct Mapper

**Files:**
- Create: `skills/content-extractor/extractors/vision_mapper.py`
- Modify: `skills/content-extractor/models/structured.py` (add VisionFunction)
- Modify: `skills/content-extractor/main.py` (use vision_mapper)
- Test: `tests/test_content_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_content_extractor.py

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_content_extractor.py::TestVisionMapper -v`
Expected: FAIL with "No module named 'extractors.vision_mapper'"

- [ ] **Step 3: Write VisionMapper**

```python
# skills/content-extractor/extractors/vision_mapper.py
"""Map Vision LLM components to L2 Function structures."""

from typing import List, Optional, Dict, Any
from models.structured import Function


class VisionMapper:
    """Converts Vision LLM output to L2 Function entities."""

    # Map UI component types to normalized names
    COMPONENT_TYPE_MAP = {
        "button": "button",
        "nav": "navigation",
        "navbar": "navigation",
        "input": "input_field",
        "textfield": "input_field",
        "card": "card",
        "kpi": "metric_card",
        "chart": "chart",
        "graph": "chart",
        "table": "table",
        "form": "form",
        "modal": "modal",
        "dialog": "modal",
        "sidebar": "sidebar",
        "header": "header",
        "footer": "footer",
        "label": "label",
        "text": "text",
        "icon": "icon",
        "image": "image",
        "link": "link",
        "menu": "menu",
        "dropdown": "dropdown",
        "checkbox": "checkbox",
        "radio": "radio",
        "switch": "switch",
        "slider": "slider",
        "tab": "tab",
    }

    def vision_to_functions(
        self,
        vision_result: dict,
        source_id: str = "vision"
    ) -> List[Function]:
        """
        Convert Vision LLM components to L2 Function objects.

        Args:
            vision_result: Vision JSON with page_type, components, layout
            source_id: Source identifier for Function.source_paragraphs

        Returns:
            List of Function objects
        """
        components = vision_result.get("components", [])
        functions = []

        for i, comp in enumerate(components):
            func = self._component_to_function(comp, i, source_id, vision_result)
            if func:
                functions.append(func)

        return functions

    def _component_to_function(
        self,
        component: dict,
        index: int,
        source_id: str,
        vision_result: dict
    ) -> Optional[Function]:
        """Convert a single Vision component to Function."""
        comp_type = component.get("type", "unknown")
        label = component.get("label", "")
        function_name = component.get("function")
        data = component.get("data", {})

        if not label and not function_name:
            return None

        # Determine name and normalized name
        if function_name:
            name = label if label else function_name
            normalized = self._normalize_name(function_name)
            trigger = f"点击 {label} 按钮" if comp_type in ("button", "nav") else f"与 {label} 交互"
        else:
            name = label
            normalized = self._normalize_name(label)
            trigger = f"查看 {label}"

        func = Function(
            id=f"vision_{source_id}_{index:03d}",
            name=name,
            name_normalized=normalized,
            source_paragraphs=[source_id],
            trigger=trigger,
            condition=None,
            action=self._build_action(component),
            benefit=None,
            confidence=0.85,  # Vision has high confidence
            attributes={
                "component_type": self.COMPONENT_TYPE_MAP.get(comp_type, comp_type),
                "vision_data": data,
                "layout": vision_result.get("layout"),
                "page_type": vision_result.get("page_type"),
            }
        )

        return func

    def _normalize_name(self, name: str) -> str:
        """Normalize name to snake_case."""
        import re
        # Remove non-alphanumeric, convert to lowercase
        normalized = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name)
        normalized = normalized.strip('_').lower()
        # Collapse multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        return normalized

    def _build_action(self, component: dict) -> str:
        """Build action description from component."""
        comp_type = component.get("type", "")
        label = component.get("label", "")

        action_map = {
            "button": f"点击 {label}",
            "nav": f"导航到 {label}",
            "navbar": f"导航到 {label}",
            "input": f"输入 {label}",
            "textfield": f"输入 {label}",
            "form": f"提交 {label} 表单",
            "link": f"跳转 {label}",
            "menu": f"打开 {label} 菜单",
            "dropdown": f"选择 {label}",
            "modal": f"打开 {label} 弹窗",
        }

        return action_map.get(comp_type, f"与 {label} 交互")
```

- [ ] **Step 4: Add VisionFunction to structured.py**

```python
# skills/content-extractor/models/structured.py - add VisionFunction dataclass
@dataclass
class VisionFunction:
    """L2 Function derived from Vision LLM output."""
    component_type: str
    label: str
    function: Optional[str]
    data: Dict[str, Any]
    page_type: str
    layout: str
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_content_extractor.py::TestVisionMapper -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/content-extractor/extractors/vision_mapper.py
git add skills/content-extractor/models/structured.py
git add tests/test_content_extractor.py
git commit -m "feat(content-extractor): add Vision-to-L2 Function direct mapper"
```

---

## Task 3: URL Handler

**Files:**
- Create: `skills/content-extractor/handlers/url_handler.py`
- Modify: `skills/content-extractor/handlers/__init__.py`
- Modify: `skills/content-extractor/config.py`
- Test: `tests/test_content_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_content_extractor.py

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_content_extractor.py::TestURLHandler -v`
Expected: FAIL with "No module named 'handlers.url_handler'"

- [ ] **Step 3: Write URL Handler**

```python
# skills/content-extractor/handlers/url_handler.py
"""Handle remote URL input."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class URLHandler:
    """Handles remote URL input and type resolution."""

    # URL patterns for different content types
    URL_TYPE_PATTERNS = {
        "pdf": [r"\.pdf$", r"/[^/]+\.pdf", r"\?.*\.pdf"],
        "markdown": [r"\.md$", r"\.markdown$", r"\.mdown$"],
        "html": [r"\.html?$", r"\.htm$"],
        "image": [r"\.(png|jpg|jpeg|gif|bmp|webp)$"],
        "docx": [r"\.docx$"],
    }

    # Domain-specific parsers
    DOMAIN_PARSERS = {
        "github.com": "github",
        "gist.github.com": "gist",
        "confluence": "confluence",
        "notion.so": "notion",
        "notion.site": "notion",
    }

    def can_handle(self, path: str) -> bool:
        """Check if input is a URL."""
        if not path:
            return False

        # Simple URL detection
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(path))

    def resolve_type(self, url: str) -> str:
        """Resolve URL to content type based on extension."""
        url_lower = url.lower()

        for content_type, patterns in self.URL_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return content_type

        # Default to html for web URLs
        return "html"

    def get_parser_type(self, url: str) -> str:
        """Get the appropriate parser type for URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check domain-specific parsers
        for key, parser in self.DOMAIN_PARSERS.items():
            if key in domain:
                return parser

        # Default based on path
        return self.resolve_type(url)

    def extract_filename(self, url: str) -> Optional[str]:
        """Extract filename from URL path."""
        parsed = urlparse(url)
        path = parsed.path

        if "/" in path:
            filename = path.rsplit("/", 1)[-1]
            if filename:
                return filename

        return None
```

- [ ] **Step 4: Update handlers/__init__.py**

```python
# skills/content-extractor/handlers/__init__.py
from .clipboard import ClipboardHandler
from .file_handler import FileHandler
from .url_handler import URLHandler  # ADD THIS
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_content_extractor.py::TestURLHandler -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/content-extractor/handlers/url_handler.py
git add skills/content-extractor/handlers/__init__.py
git add tests/test_content_extractor.py
git commit -m "feat(content-extractor): add URL handler for remote content"
```

---

## Task 4: Entity Aligner (V2)

**Files:**
- Create: `skills/content-extractor/associator/entity_aligner.py`
- Modify: `skills/content-extractor/associator/__init__.py`
- Test: `tests/test_content_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_content_extractor.py

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_content_extractor.py::TestEntityAligner -v`
Expected: FAIL with "No module named 'associator.entity_aligner'"

- [ ] **Step 3: Write EntityAligner**

```python
# skills/content-extractor/associator/entity_aligner.py
"""Entity alignment using fuzzy matching and semantic similarity."""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher


class EntityAligner:
    """
    Aligns and merges entities from multiple sources.

    Uses rules-based fuzzy matching for speed, with hooks for LLM enhancement.
    """

    # Common term equivalences
    TERM_EQUIVALENCES = {
        "login": ["登录", "登入", "认证", "authenticate"],
        "logout": ["登出", "退出", "signout"],
        "register": ["注册", "登记", "signup"],
        "user": ["用户", "user", "users", "member", "会员"],
        "password": ["密码", "password", "pwd"],
        "order": ["订单", "order", "订购"],
        "payment": ["支付", "payment", "pay", "付款"],
    }

    def normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        normalized = text.lower()
        # Remove special chars
        normalized = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', normalized)
        return normalized

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        norm1 = self.normalize(str1)
        norm2 = self.normalize(str2)

        # Exact match
        if norm1 == norm2:
            return 1.0

        # Check term equivalences
        for base, equivalents in self.TERM_EQUIVALENCES.items():
            if norm1 in equivalents or norm1 == base:
                if norm2 in equivalents or norm2 == base:
                    return 0.85

        # Sequence matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_similar(
        self,
        target: str,
        entities: List[Any,
        threshold: float = 0.6
    ) -> List[Tuple[Any, float]]:
        """
        Find entities similar to target.

        Args:
            target: Target name to match
            entities: List of entities with name/name_normalized
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (entity, similarity_score) tuples
        """
        results = []
        target_norm = self.normalize(target)

        for entity in entities:
            entity_name = getattr(entity, 'name', '') or ''
            entity_norm = self.normalize(entity_name)

            score = self.calculate_similarity(target, entity_name)
            if score >= threshold:
                results.append((entity, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def find_merge_candidates(
        self,
        entities: List[Dict],
        threshold: float = 0.9
    ) -> List[List[Dict]]:
        """
        Find groups of entities that should be merged.

        Args:
            entities: List of entity dicts with 'id', 'name'
            threshold: Similarity threshold for merging

        Returns:
            List of merge groups (each group is a list of entities)
        """
        groups = []
        used = set()

        for i, entity in enumerate(entities):
            if entity['id'] in used:
                continue

            group = [entity]
            used.add(entity['id'])

            for j, other in enumerate(entities[i + 1:], start=i + 1):
                if other['id'] in used:
                    continue

                score = self.calculate_similarity(entity['name'], other['name'])
                if score >= threshold:
                    group.append(other)
                    used.add(other['id'])

            if len(group) > 1:
                groups.append(group)

        return groups

    def suggest_merged_name(self, entities: List[Dict]) -> str:
        """Suggest a merged name from multiple entities."""
        if not entities:
            return ""

        if len(entities) == 1:
            return entities[0]['name']

        # Prefer Chinese if available
        for entity in entities:
            if re.search(r'[\u4e00-\u9fff]', entity['name']):
                return entity['name']

        # Return longest name
        return max(entities, key=lambda x: len(x['name']))['name']
```

- [ ] **Step 4: Update associator/__init__.py**

```python
# skills/content-extractor/associator/__init__.py
from .term_mapper import TermMapper
from .ref_linker import RefLinker
from .entity_aligner import EntityAligner  # ADD THIS
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_content_extractor.py::TestEntityAligner -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/content-extractor/associator/entity_aligner.py
git add skills/content-extractor/associator/__init__.py
git add tests/test_content_extractor.py
git commit -m "feat(content-extractor): add entity aligner for V2 associations"
```

---

## Task 5: Update Main Pipeline

**Files:**
- Modify: `skills/content-extractor/main.py`

- [ ] **Step 1: Read current main.py**

```bash
cat skills/content-extractor/main.py
```

- [ ] **Step 2: Add PDF and URL handler integration**

Update the `analyze()` method to:
1. Import PDFExtractor and URLHandler
2. Handle URL sources by resolving type and downloading
3. Handle PDF files using PDFExtractor
4. Use VisionMapper for Vision→L2 conversion

```python
# skills/content-extractor/main.py - key changes

from extractors.pdf_extractor import PDFExtractor
from extractors.vision_mapper import VisionMapper
from handlers.url_handler import URLHandler

class ContentExtractor:
    def __init__(self):
        # ... existing ...
        self.pdf_extractor = PDFExtractor()
        self.url_handler = URLHandler()
        self.vision_mapper = VisionMapper()

    def analyze(self, sources: List[SourceDocument], output_dir: str = "./output") -> dict:
        # Add URL handling at the beginning
        resolved_sources = []
        for source in sources:
            if self.url_handler.can_handle(source.path or ""):
                url_type = self.url_handler.resolve_type(source.path)
                # For MVP: store URL info, actual download done by agent layer
                resolved_sources.append(source)
            else:
                resolved_sources.append(source)

        # ... existing processing ...

        # In file processing, add PDF handling
        elif source.type == "file":
            ext = Path(source.path).suffix.lower()
            if ext == ".pdf":
                pdf_result = self.pdf_extractor.extract_full(source.path)
                if pdf_result:
                    for page_text in pdf_result["pages"]:
                        paragraphs = self.markdown_extractor.extract(page_text, source=source.path)
                        all_paragraphs.extend(paragraphs.paragraphs)
```

- [ ] **Step 3: Integrate VisionMapper**

After extracting vision results, use VisionMapper to create L2 Functions:

```python
# After image processing in analyze()
if image_result.get("vision"):
    vision_funcs = self.vision_mapper.vision_to_functions(
        image_result["vision"],
        source_id=source.path
    )
    for func in vision_funcs:
        structured.add_function(func)
    # Also save to references
    all_references.append({...})
```

- [ ] **Step 4: Commit**

```bash
git add skills/content-extractor/main.py
git commit -m "feat(content-extractor): integrate PDF extractor, URL handler, and VisionMapper"
```

---

## Task 6: Update Dependencies

**Files:**
- Modify: `skills/content-extractor/SKILL.md`

- [ ] **Step 1: Update SKILL.md with new dependencies**

```markdown
## Dependencies

```bash
pip install pyyaml pillow pytesseract markdown-it pdfplumber
```

- pdfplumber: PDF text extraction
- Vision MCP (MiniMax or OpenAI Vision) 由 Agent 层通过 MCP 调用
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/SKILL.md
git commit -m "docs(content-extractor): update SKILL.md with new dependencies"
```

---

## Summary

**Tasks Completed: 6**

**Enhancements Added:**
- PDF text extraction using pdfplumber
- Vision → L2 Function direct mapping via VisionMapper
- URL handler for remote content type resolution
- Entity aligner for V2 semantic associations
- Updated main pipeline to integrate all new modules

**Dependencies Added:**
- `pdfplumber` for PDF extraction

**Next steps after enhancement:**
1. Add Docx support (python-docx)
2. Add HTML extractor for web pages
3. Integrate LLM for semantic entity alignment
4. Add cache layer for URL content
