# Content Extractor MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MVP of content-extractor skill - parses heterogeneous documents (text/markdown/files/images), extracts requirements, associates them, outputs Markdown report + JSON.

**Architecture:** Rule-first + LLM-enhancement hybrid. L1 (paragraph index) preserves raw text, L2 (structured) provides machine-readable output. Three-layer association: term mapping (rules) + cross-doc references (regex) + entity alignment (LLM).

**Image Processing Flow:**
```
图片输入 → [外部 OCR/Vision MCP] → extract_full(path, vision_result)
                                 ↓
         combined_text = OCR文本 + Vision结构化描述
         vision = 原始结构化数据（components/layout/design_tools）
                                 ↓
         L2: 从 components 直接构建 Function（不经过 MarkdownExtractor）
         refs: vision_analysis 保留完整 JSON
```

**Tech Stack:** Python, PyYAML, markdown-it, pytesseract (local OCR备选), Vision LLM MCP (外部)

**Key Design Decisions (从实践中发现):**
1. Vision provider 由调用方通过 `set_vision_provider(fn)` 注册，Python层不依赖特定MCP
2. 图片的 L2 结构从 Vision components 直接构建，绕过 MarkdownExtractor 的分句逻辑
3. Vision 分析结果通过 `SourceDocument.vision` 注入，通过 `all_references` 保存到 JSON
4. UI 原型图片（碎片化标签）与 PRD 文档（自然语言）适用不同提取路径

---

## File Structure

```
skills/content-extractor/
├── SKILL.md
├── config.py
├── handlers/
│   ├── __init__.py
│   ├── clipboard.py        # Text paste input
│   └── file_handler.py     # Local file reading
├── extractors/
│   ├── __init__.py
│   ├── markdown_extractor.py
│   └── image_extractor.py  # OCR
├── associator/
│   ├── __init__.py
│   ├── term_mapper.py      # Term dictionary lookup
│   └── ref_linker.py       # Cross-doc reference extraction
├── dictionaries/
│   └── base_terms.yaml     # 50-80 core terms
├── merger/
│   ├── __init__.py
│   ├── conflict_resolver.py
│   └── graph_builder.py
├── output/
│   ├── __init__.py
│   ├── markdown_report.py
│   └── json_exporter.py
├── models/
│   ├── __init__.py
│   ├── paragraph.py        # L1 data model
│   └── structured.py       # L2 data model
└── main.py                 # Entry point
```

---

## Task 1: Project Setup

**Files:**
- Create: `skills/content-extractor/SKILL.md`
- Create: `skills/content-extractor/__init__.py`
- Create: `skills/content-extractor/config.py`

- [ ] **Step 1: Create SKILL.md**

```markdown
# Content Extractor

Parses heterogeneous documents (text/markdown/files/images), extracts requirements, and associates them.

## Usage

### Input Methods

**1. Text Paste (in conversation)**
Paste markdown or text content directly.

**2. Config File**
```yaml
input:
  documents:
    - type: file
      path: ./docs/requirements.md
```

### Output

- Markdown report: `requirements-report.md`
- JSON structured: `requirements-report.json`

## Architecture

- L1: Paragraph index (preserves raw text)
- L2: Structured data (machine-readable)
- Three-layer association: term mapping → reference linking → entity alignment
```

- [ ] **Step 2: Create __init__.py**

```python
# Content Extractor Package
```

- [ ] **Step 3: Create config.py**

```python
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
    vision: Optional[dict] = None  # 预提取的视觉分析结果（来自 LLM Vision MCP）


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
```

- [ ] **Step 4: Commit**

```bash
git add skills/content-extractor/SKILL.md skills/content-extractor/__init__.py skills/content-extractor/config.py
git commit -m "feat(content-extractor): initial project setup with SKILL.md and config"
```

---

## Task 2: Data Models

**Files:**
- Create: `skills/content-extractor/models/__init__.py`
- Create: `skills/content-extractor/models/paragraph.py`
- Create: `skills/content-extractor/models/structured.py`

- [ ] **Step 1: Create models/__init__.py**

```python
# Models Package
from .paragraph import Paragraph, Sentence, ParagraphCollection
from .structured import Function, StructuredData, ExtractedData
```

- [ ] **Step 2: Create paragraph.py (L1 model)**

```python
"""L1: Paragraph Index Model - preserves raw text."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Sentence:
    id: str
    text: str
    role: str  # trigger, condition, action, result


@dataclass
class SentenceRelation:
    from_id: str
    to_id: str
    type: str  # if_then, cause_effect, etc.


@dataclass
class Paragraph:
    id: str
    source: str  # "filename.md#3.2.1"
    section: str
    raw_text: str
    semantic_unit: bool = True

    sentences: List[Sentence] = field(default_factory=list)
    sentence_relations: List[SentenceRelation] = field(default_factory=list)

    # Metadata
    confidence: float = 1.0
    needs_review: bool = False


@dataclass
class ParagraphCollection:
    paragraphs: List[Paragraph] = field(default_factory=list)

    def add(self, paragraph: Paragraph):
        self.paragraphs.append(paragraph)

    def get_by_id(self, para_id: str) -> Optional[Paragraph]:
        for p in self.paragraphs:
            if p.id == f"para_{para_id}" or p.id == para_id:
                return p
        return None
```

- [ ] **Step 3: Create structured.py (L2 model)**

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add skills/content-extractor/models/
git commit -m "feat(content-extractor): add L1/L2 data models"
```

---

## Task 3: Base Terminology Dictionary

**Files:**
- Create: `skills/content-extractor/dictionaries/__init__.py`
- Create: `skills/content-extractor/dictionaries/base_terms.yaml`

- [ ] **Step 1: Create dictionaries/__init__.py**

```python
# Dictionaries Package
import yaml
from pathlib import Path
from typing import Dict, List, Set


class TermDictionary:
    """Term dictionary for association mapping."""

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = Path(__file__).parent / "base_terms.yaml"
        self.base_path = Path(base_path)
        self.terms: Dict[str, List[str]] = {}
        self.reverse_map: Dict[str, str] = {}  # synonym -> canonical
        self._load()

    def _load(self):
        """Load dictionary from YAML."""
        if not self.base_path.exists():
            return

        with open(self.base_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for canonical, synonyms in data.items():
            self.terms[canonical] = synonyms
            for syn in synonyms:
                self.reverse_map[syn.lower()] = canonical

    def get_canonical(self, term: str) -> str:
        """Get canonical form of a term."""
        return self.reverse_map.get(term.lower(), term.lower())

    def get_synonyms(self, term: str) -> List[str]:
        """Get all synonyms for a term."""
        canonical = self.get_canonical(term)
        return self.terms.get(canonical, [term])

    def find_matching_terms(self, text: str) -> Set[str]:
        """Find all matching terms in text."""
        text_lower = text.lower()
        matches = set()
        for term, synonyms in self.terms.items():
            for syn in synonyms:
                if syn.lower() in text_lower:
                    matches.add(term)
                    break
        return matches
```

- [ ] **Step 2: Create base_terms.yaml**

```yaml
# Base terminology dictionary (50-80 core terms)
# Used for term mapping in association - NOT passed to LLM

user:
  - user
  - 用户
  - users
  - account
  - 账户
  - 账号

auth:
  - login
  - sign_in
  - 登录
  - 认证
  - authenticate
  - authentication
  - 验证
  - signin

password:
  - password
  - 密码
  - pwd
  - passwd

payment:
  - pay
  - payment
  - 支付
  - 结账
  - checkout
  - settle
  - 结算

order:
  - order
  - 订单
  - 订购
  - purchase
  - 购买

refund:
  - refund
  - 退款
  - 退费
  - 退货
  - return

vip:
  - vip
  - 会员
  - 会员等级
  - premium
  - 高级用户

discount:
  - discount
  - 折扣
  - 优惠
  - coupon
  - 优惠券

points:
  - points
  - 积分
  - credit
  - score

notification:
  - notification
  - 通知
  - 消息
  - message
  - push
  - 推送

register:
  - register
  - 注册
  - signup
  - 登记

logout:
  - logout
  - 登出
  - signout
  - 退出

admin:
  - admin
  - 管理员
  - administration
  - 管理

api:
  - api
  - 接口
  - endpoint
  - 服务端点

database:
  - database
  - db
  - 数据库
  - data

file:
  - file
  - 文件
  - upload
  - 上传
  - download
  - 下载

email:
  - email
  - 邮件
  - e-mail
  - 邮箱

phone:
  - phone
  - 手机
  - mobile
  - 电话
  - tel

verification:
  - verification
  - 验证码
  - verify
  - code
  - 校验
  - 验证
```

- [ ] **Step 3: Commit**

```bash
git add skills/content-extractor/dictionaries/
git commit -m "feat(content-extractor): add base terminology dictionary"
```

---

## Task 4: Input Handlers

**Files:**
- Create: `skills/content-extractor/handlers/__init__.py`
- Create: `skills/content-extractor/handlers/clipboard.py`
- Create: `skills/content-extractor/handlers/file_handler.py`

- [ ] **Step 1: Create handlers/__init__.py**

```python
# Handlers Package
from .clipboard import ClipboardHandler
from .file_handler import FileHandler
```

- [ ] **Step 2: Create clipboard.py**

```python
"""Handle text paste input."""

from typing import List, Tuple


class ClipboardHandler:
    """Handles pasted text content."""

    def parse(self, content: str) -> List[Tuple[str, str]]:
        """
        Parse pasted content.

        Returns:
            List of (content_type, content) tuples.
            content_type: "markdown", "text"
        """
        if not content or not content.strip():
            return []

        content = content.strip()

        # Detect if markdown
        if self._is_markdown(content):
            return [("markdown", content)]
        else:
            return [("text", content)]

    def _is_markdown(self, content: str) -> bool:
        """Simple markdown detection."""
        markdown_indicators = [
            '#',           # Headers
            '```',         # Code blocks
            '- ',          # Lists
            '* ',          # Lists
            '[ ]',         # Checkboxes
            '**',          # Bold
            '__',          # Bold
            '```'          # Code
        ]
        return any(content.startswith(ind) or f'\n{ind}' in content
                   for ind in markdown_indicators)
```

- [ ] **Step 3: Create file_handler.py**

```python
"""Handle local file input."""

import os
from pathlib import Path
from typing import List, Tuple, Optional


class FileHandler:
    """Handles local file reading."""

    SUPPORTED_EXTENSIONS = {
        '.md', '.markdown', '.txt',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp'  # Images for OCR
    }

    def can_handle(self, path: str) -> bool:
        """Check if file is supported."""
        ext = Path(path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def read(self, path: str) -> Optional[Tuple[str, str]]:
        """
        Read file content.

        Returns:
            (content_type, content) or None if unsupported
        """
        if not os.path.exists(path):
            return None

        ext = Path(path).suffix.lower()

        if ext in ('.md', '.markdown', '.txt'):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ("markdown" if ext in ('.md', '.markdown') else "text", content)

        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp'):
            return ("image", path)  # Return path for OCR processing

        return None

    def list_files(self, directory: str, recursive: bool = False) -> List[str]:
        """List supported files in directory."""
        files = []
        path = Path(directory)

        if recursive:
            for ext in self.SUPPORTED_EXTENSIONS:
                files.extend([str(p) for p in path.rglob(f'*{ext}')])
        else:
            for ext in self.SUPPORTED_EXTENSIONS:
                files.extend([str(p) for p in path.glob(f'*{ext}')])

        return files
```

- [ ] **Step 4: Commit**

```bash
git add skills/content-extractor/handlers/
git commit -m "feat(content-extractor): add input handlers for clipboard and files"
```

---

## Task 5: Markdown Extractor

**Files:**
- Create: `skills/content-extractor/extractors/__init__.py`
- Create: `skills/content-extractor/extractors/markdown_extractor.py`

- [ ] **Step 1: Create extractors/__init__.py**

```python
# Extractors Package
from .markdown_extractor import MarkdownExtractor
from .image_extractor import ImageExtractor
```

- [ ] **Step 2: Create markdown_extractor.py**

```python
"""Extract content from Markdown/Text documents."""

import re
from typing import List
from models.paragraph import Paragraph, Sentence, SentenceRelation, ParagraphCollection


class MarkdownExtractor:
    """Extracts L1 paragraphs and L2 structured data from markdown."""

    def extract(self, content: str, source: str = "document.md") -> ParagraphCollection:
        """
        Extract paragraphs from markdown content.

        Args:
            content: Markdown text content
            source: Source identifier

        Returns:
            ParagraphCollection with extracted paragraphs
        """
        paragraphs = ParagraphCollection()

        # Split by double newlines (paragraph separation)
        blocks = re.split(r'\n\s*\n', content)

        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue

            para_id = f"para_{i+1:03d}"

            # Detect section header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', block, re.MULTILINE)
            section = ""
            if header_match:
                section = header_match.group(2).strip()

            # Extract sentences and roles
            sentences = self._extract_sentences(block, para_id)
            relations = self._extract_relations(sentences)

            paragraph = Paragraph(
                id=para_id,
                source=f"{source}#{para_id}",
                section=section,
                raw_text=block,
                semantic_unit=True,
                sentences=sentences,
                sentence_relations=relations
            )

            paragraphs.add(paragraph)

        return paragraphs

    def _extract_sentences(self, text: str, para_id: str) -> List[Sentence]:
        """Extract sentences and their roles from text."""
        # Simple sentence splitting
        sentence_texts = re.split(r'[。！？\n]', text)
        sentences = []

        for i, sent in enumerate(sentence_texts):
            sent = sent.strip()
            if not sent:
                continue

            role = self._infer_role(sent)
            sentences.append(Sentence(
                id=f"{para_id}_s{i+1}",
                text=sent,
                role=role
            ))

        return sentences

    def _infer_role(self, sentence: str) -> str:
        """Infer the role of a sentence."""
        sentence_lower = sentence.lower()

        # Trigger indicators
        trigger_patterns = ['当', '用户', '如果', 'when', 'if', 'after', '登录']
        for p in trigger_patterns:
            if p in sentence_lower:
                return "trigger"

        # Condition indicators
        cond_patterns = ['如果', '满足', '条件', 'when', 'if', '条件是']
        for p in cond_patterns:
            if p in sentence_lower:
                return "condition"

        # Action indicators
        action_patterns = ['自动', '发送', '创建', '更新', '删除', '跳转', 'action', 'do']
        for p in action_patterns:
            if p in sentence_lower:
                return "action"

        # Result indicators
        result_patterns = ['享受', '获得', '收到', 'result', 'then']
        for p in result_patterns:
            if p in sentence_lower:
                return "result"

        return "statement"

    def _extract_relations(self, sentences: List[Sentence]) -> List[SentenceRelation]:
        """Extract relations between sentences."""
        relations = []

        for i, sent in enumerate(sentences):
            if sent.role == "condition" and i + 1 < len(sentences):
                next_sent = sentences[i + 1]
                if next_sent.role == "action":
                    relations.append(SentenceRelation(
                        from_id=sent.id,
                        to_id=next_sent.id,
                        type="if_then"
                    ))

        return relations
```

- [ ] **Step 3: Commit**

```bash
git add skills/content-extractor/extractors/markdown_extractor.py
git commit -m "feat(content-extractor): add markdown extractor with sentence role inference"
```

---

## Task 6: Image Extractor (OCR + Vision Provider)

**Files:**
- Create: `skills/content-extractor/extractors/image_extractor.py`

- [ ] **Step 1: Create image_extractor.py**

```python
"""Extract text from images using OCR or external vision providers."""

from typing import Optional, Callable
import os


class ImageExtractor:
    """
    Extracts text and visual information from images.

    Supports two modes:
    1. Internal OCR: uses pytesseract (if available)
    2. External providers: registered via set_*_provider() methods

    Priority: External provider > Internal OCR
    """

    def __init__(self):
        self._ocr_available = None
        self._external_ocr: Optional[Callable] = None
        self._external_vision: Optional[Callable] = None

    def set_ocr_provider(self, fn: Callable[[str], Optional[str]]) -> None:
        """Register an external OCR provider (MCP/第三方服务)."""
        self._external_ocr = fn

    def set_vision_provider(self, fn: Callable[[str], Optional[dict]]) -> None:
        """
        Register an external vision/LLM provider.

        The fn should return dict with:
        - page_type: str
        - components: [{"type", "label", "function", "data"}, ...]
        - layout: str
        - design_tools: [str, ...]
        - design_system: str
        """
        self._external_vision = fn

    @property
    def has_ocr(self) -> bool:
        """Check if any OCR is available."""
        return self._external_ocr is not None or self._ocr_available is True

    @property
    def has_vision(self) -> bool:
        """Check if vision capability is available."""
        return self._external_vision is not None

    def extract(self, image_path: str) -> Optional[str]:
        """OCR: External provider > Internal pytesseract."""
        if not os.path.exists(image_path):
            return None
        # 1. 外部 OCR provider（优先）
        if self._external_ocr is not None:
            try:
                result = self._external_ocr(image_path)
                return result.strip() if result else None
            except Exception as e:
                print(f"External OCR failed: {e}")
        # 2. 内部 pytesseract
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(image_path)
            return pytesseract.image_to_string(image, lang='eng+chi').strip()
        except Exception:
            return None

    def extract_with_vision(self, image_path: str, prompt: str = None) -> Optional[dict]:
        """Vision: 仅使用外部 provider。"""
        if not os.path.exists(image_path):
            return None
        if self._external_vision is not None:
            try:
                return self._external_vision(image_path)
            except Exception as e:
                print(f"External vision failed: {e}")
        return None

    def extract_full(self, image_path: str, vision_result: dict = None) -> dict:
        """
        完整提取：OCR + Vision 两层信息。

        Args:
            image_path: 图片路径
            vision_result: 预提取的 Vision 结果（来自 LLM MCP）

        Returns:
            dict: {
                "ref": str,
                "ocr_text": str or None,
                "has_ocr": bool,
                "vision": dict or None,
                "has_vision": bool,
                "combined_text": str  # OCR + Vision 文本，供 MarkdownExtractor 处理
            }
        """
        result = {
            "ref": image_path,
            "type": "image",
            "ocr_text": None,
            "has_ocr": False,
            "vision": vision_result,
            "has_vision": vision_result is not None,
            "combined_text": "",
        }

        # 1. OCR
        ocr_text = self.extract(image_path)
        if ocr_text:
            result["ocr_text"] = ocr_text
            result["has_ocr"] = True
            result["combined_text"] = ocr_text

        # 2. Vision（优先用外部 provider）
        if vision_result:
            result["vision"] = vision_result
            result["has_vision"] = True
            result["combined_text"] += "\n" + self._vision_to_text(vision_result)
        else:
            internal = self.extract_with_vision(image_path)
            if internal:
                result["vision"] = internal
                result["has_vision"] = True
                result["combined_text"] += "\n" + self._vision_to_text(internal)

        return result

    def _vision_to_text(self, vision: dict) -> str:
        """将 Vision 结果转为可读文本。"""
        lines = []
        if vision.get("page_type"):
            lines.append(f"页面类型: {vision['page_type']}")
        if vision.get("design_tools"):
            lines.append(f"设计工具: {', '.join(vision['design_tools'])}")
        if vision.get("design_system"):
            lines.append(f"设计系统: {vision['design_system']}")
        if vision.get("layout"):
            lines.append(f"布局结构: {vision['layout']}")
        if vision.get("components"):
            lines.append("组件列表:")
            for comp in vision["components"]:
                data_str = f" (数据: {comp['data']})" if comp.get("data") else ""
                lines.append(f"  - [{comp['type']}] {comp['label']}: {comp.get('function', '')}{data_str}")
        return "\n".join(lines)

    def extract_with_metadata(self, image_path: str) -> dict:
        """Legacy method: extract text and image metadata."""
        full_result = self.extract_full(image_path)
        return {
            "ref": image_path,
            "type": "image",
            "ocr_text": full_result["ocr_text"] or "",
            "has_text": full_result["has_ocr"],
            "vision": full_result["vision"],
            "needs_vision_model": not full_result["has_vision"],
            "visual_note": f"OCR: {len(full_result.get('ocr_text') or '')} chars, Vision: {'✓' if full_result['has_vision'] else '✗'}"
        }
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/extractors/image_extractor.py
git commit -m "feat(content-extractor): add OCR + Vision provider support to image extractor"
```

---

## Task 7: Term Mapper (Association Layer 1)

**Files:**
- Create: `skills/content-extractor/associator/term_mapper.py`

- [ ] **Step 1: Create term_mapper.py**

```python
"""Term-based association using dictionary lookup."""

from typing import List, Set, Tuple
from models.structured import Function
from dictionaries import TermDictionary


class TermMapper:
    """Maps terms between documents using dictionary lookup."""

    def __init__(self, dictionary: TermDictionary = None):
        self.dictionary = dictionary or TermDictionary()

    def extract_terms(self, text: str) -> Set[str]:
        """Extract all matching terms from text."""
        return self.dictionary.find_matching_terms(text)

    def find_associations(
        self,
        source_terms: Set[str],
        target_candidates: List[Function]
    ) -> List[Tuple[Function, float]]:
        """
        Find associations based on term overlap.

        Returns:
            List of (function, confidence) tuples
        """
        associations = []

        for func in target_candidates:
            score = self._calculate_term_overlap(source_terms, func)
            if score > 0:
                associations.append((func, score))

        # Sort by score descending
        associations.sort(key=lambda x: x[1], reverse=True)
        return associations

    def _calculate_term_overlap(self, source_terms: Set[str], func: Function) -> float:
        """Calculate term overlap score between source and function."""
        if not source_terms:
            return 0.0

        # Get terms from function name
        func_terms = self.extract_terms(func.name)
        func_terms.update(self.extract_terms(func.name_normalized))

        # Get terms from extracted fields
        for field_value in [func.trigger, func.condition, func.action, func.benefit]:
            if field_value:
                func_terms.update(self.extract_terms(field_value))

        if not func_terms:
            return 0.0

        # Jaccard similarity
        intersection = source_terms & func_terms
        union = source_terms | func_terms

        return len(intersection) / len(union) if union else 0.0

    def build_term_normalized(self, text: str) -> str:
        """Build normalized term from text using dictionary."""
        terms = self.extract_terms(text)
        if terms:
            return "_".join(sorted(terms))
        return text.lower().replace(" ", "_")
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/associator/term_mapper.py
git commit -m "feat(content-extractor): add term mapper for dictionary-based association"
```

---

## Task 8: Reference Linker (Association Layer 2)

**Files:**
- Create: `skills/content-extractor/associator/ref_linker.py`

- [ ] **Step 1: Create ref_linker.py**

```python
"""Cross-document reference extraction and linking."""

import re
from typing import List, Dict, Tuple, Optional


class RefLinker:
    """Extracts and resolves cross-document references."""

    # Reference patterns
    CROSS_DOC_PATTERNS = [
        r"详见[《"]?(.+?)[》文档手册]",
        r"参见[《"]?(.+?)[》\]]",
        r"[《"]?(.+?)[》\]]\s*[第见]?\s*([0-9.]+)章?",
    ]

    SECTION_PATTERNS = [
        r"见第?([0-9.]+)节?",
        r"如图?([0-9]+(?:\.[0-9]+)?)",
        r"参考第?([0-9.]+)节"
    ]

    URL_PATTERN = r"https?://[^\s<>\"]+"

    def extract_references(self, text: str) -> List[Dict]:
        """
        Extract all types of references from text.

        Returns:
            List of reference dicts with type, target, and confidence
        """
        references = []

        # Cross-document references
        for pattern in self.CROSS_DOC_PATTERNS:
            for match in re.finditer(pattern, text):
                references.append({
                    "type": "cross_doc",
                    "target": match.group(1).strip(),
                    "confidence": 0.95,  # High confidence for explicit refs
                    "match": match.group(0)
                })

        # Section references
        for pattern in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                section = match.group(1)
                references.append({
                    "type": "section",
                    "target": f"section_{section}",
                    "confidence": 0.9,
                    "match": match.group(0)
                })

        # URLs
        for match in re.finditer(self.URL_PATTERN, text):
            references.append({
                "type": "url",
                "target": match.group(0),
                "confidence": 0.85,
                "match": match.group(0)
            })

        return references

    def resolve_reference(
        self,
        ref: Dict,
        known_entities: Dict[str, List[str]]
    ) -> Optional[str]:
        """
        Resolve reference to entity ID.

        Args:
            ref: Reference dict
            known_entities: Dict[entity_name, entity_ids]

        Returns:
            Resolved entity ID or None
        """
        target = ref["target"]

        # Direct match
        if target in known_entities:
            return known_entities[target][0]  # Return first match

        # Fuzzy match
        target_lower = target.lower()
        for name, ids in known_entities.items():
            if target_lower in name.lower() or name.lower() in target_lower:
                return ids[0]

        return None
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/associator/ref_linker.py
git commit -m "feat(content-extractor): add reference linker for cross-doc associations"
```

---

## Task 9: Conflict Resolver

**Files:**
- Create: `skills/content-extractor/merger/__init__.py`
- Create: `skills/content-extractor/merger/conflict_resolver.py`

- [ ] **Step 1: Create merger/__init__.py**

```python
# Merger Package
from .conflict_resolver import ConflictResolver
from .graph_builder import GraphBuilder
```

- [ ] **Step 2: Create conflict_resolver.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add skills/content-extractor/merger/conflict_resolver.py
git commit -m "feat(content-extractor): add conflict resolver with authority-based resolution"
```

---

## Task 10: Graph Builder

**Files:**
- Create: `skills/content-extractor/merger/graph_builder.py`

- [ ] **Step 1: Create graph_builder.py**

```python
"""Build functionality graph from extracted data."""

from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str  # functionality, api_endpoint, ui_page
    name: str
    parent: str = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    type: str  # implements, rendered_as, depends_on
    confidence: float = 1.0


class GraphBuilder:
    """Builds functionality graph from extracted functions."""

    def __init__(self):
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []

    def add_function(self, func_id: str, name: str, func_type: str = "functionality", metadata: Dict = None):
        """Add a node to the graph."""
        node = GraphNode(
            id=func_id,
            type=func_type,
            name=name,
            metadata=metadata or {}
        )
        self.nodes.append(node)
        return node

    def add_edge(self, from_id: str, to_id: str, edge_type: str, confidence: float = 1.0):
        """Add an edge to the graph."""
        edge = GraphEdge(
            from_id=from_id,
            to_id=to_id,
            type=edge_type,
            confidence=confidence
        )
        self.edges.append(edge)
        return edge

    def link_function_to_api(self, func_id: str, api_id: str, api_name: str, confidence: float = 0.9):
        """Link a function to its API implementation."""
        # Add API node if not exists
        if not self._node_exists(api_id):
            self.add_function(api_id, api_name, "api_endpoint")

        self.add_edge(func_id, api_id, "implemented_by", confidence)

    def link_function_to_ui(self, func_id: str, ui_id: str, ui_name: str, confidence: float = 0.7):
        """Link a function to its UI representation."""
        if not self._node_exists(ui_id):
            self.add_function(ui_id, ui_name, "ui_page")

        self.add_edge(func_id, ui_id, "rendered_as", confidence)

    def _node_exists(self, node_id: str) -> bool:
        """Check if node exists."""
        return any(n.id == node_id for n in self.nodes)

    def to_dict(self) -> Dict:
        """Export graph as dictionary."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "name": n.name,
                    "parent": n.parent,
                    **n.metadata
                }
                for n in self.nodes
            ],
            "edges": [
                {"from": e.from_id, "to": e.to_id, "type": e.type, "confidence": e.confidence}
                for e in self.edges
            ]
        }

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the graph."""
        # Simple DFS cycle detection
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for edge in self.edges:
                if edge.from_id == node_id:
                    neighbor = edge.to_id
                    if neighbor not in visited:
                        dfs(neighbor, path[:])
                    elif neighbor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:])

            rec_stack.remove(node_id)

        for node in self.nodes:
            if node.id not in visited:
                dfs(node.id, [])

        return cycles
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/merger/graph_builder.py
git commit -m "feat(content-extractor): add graph builder for functionality visualization"
```

---

## Task 11: Output Formatters

**Files:**
- Create: `skills/content-extractor/output/__init__.py`
- Create: `skills/content-extractor/output/markdown_report.py`
- Create: `skills/content-extractor/output/json_exporter.py`

- [ ] **Step 1: Create output/__init__.py**

```python
# Output Package
from .markdown_report import MarkdownReportGenerator
from .json_exporter import JSONExporter
```

- [ ] **Step 2: Create markdown_report.py**

```python
"""Generate Markdown report from extracted data."""

from typing import List
from datetime import datetime
from models.paragraph import Paragraph
from models.structured import Function, StructuredData
from merger.conflict_resolver import Conflict


class MarkdownReportGenerator:
    """Generates Markdown reports."""

    def generate(
        self,
        paragraphs: List[Paragraph],
        structured: StructuredData,
        conflicts: List[Conflict],
        sources: List[str]
    ) -> str:
        """Generate complete Markdown report."""
        lines = []

        # Header
        lines.append("# Requirements Analysis Report")
        lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        # Sources
        lines.append("## Sources")
        for source in sources:
            lines.append(f"- {source}")
        lines.append("")

        # Functions
        lines.append("## Extracted Functions")
        for func in structured.functions:
            lines.append(f"\n### {func.name}")
            lines.append(f"- ID: `{func.id}`")
            lines.append(f"- Normalized: `{func.name_normalized}`")

            if func.trigger:
                lines.append(f"- **Trigger**: {func.trigger}")
            if func.condition:
                lines.append(f"- **Condition**: {func.condition}")
            if func.action:
                lines.append(f"- **Action**: {func.action}")
            if func.benefit:
                lines.append(f"- **Benefit**: {func.benefit}")

            lines.append(f"- Confidence: {func.confidence:.2f}")

            if func.source_paragraphs:
                lines.append(f"- Source: {', '.join(func.source_paragraphs)}")

        # Conflicts section
        unresolved = [c for c in conflicts if not c.resolved]
        if unresolved:
            lines.append("\n## Pending Review Items")
            lines.append(f"\n*Found {len(unresolved)} items needing review*\n")

            for i, conflict in enumerate(unresolved, 1):
                lines.append(f"\n### {i}. [{conflict.id}] {conflict.field} - {conflict.severity.upper()}")
                lines.append(f"\n**Severity**: {conflict.severity}")
                lines.append("\n**Conflicting Values:**")
                for val in conflict.values:
                    lines.append(f"- {val['source']}: \"{val['content']}\" (authority: {val.get('authority', 'unknown')})")

                lines.append(f"\n**Suggestion**: {conflict.values[0]['content'] if conflict.values else 'Review required'}")

        lines.append("\n---\n")
        lines.append("*End of Report*")

        return "\n".join(lines)
```

- [ ] **Step 3: Create json_exporter.py**

```python
"""Export extracted data as JSON."""

import json
from datetime import datetime
from typing import List, Dict
from models.paragraph import Paragraph
from models.structured import Function, StructuredData
from merger.conflict_resolver import Conflict


class JSONExporter:
    """Exports extracted data as JSON."""

    def export(
        self,
        paragraphs: List[Paragraph],
        structured: StructuredData,
        conflicts: List[Conflict],
        sources: List[str],
        references: List[Dict] = None,
        actions: List[Dict] = None
    ) -> str:
        """Export complete data as JSON string."""
        data = {
            "metadata": {
                "module": "content-extractor",
                "version": "1.0.0",
                "sources": sources,
                "extracted_at": datetime.now().isoformat(),
                "stats": {
                    "total_paragraphs": len(paragraphs),
                    "total_functions": len(structured.functions),
                    "conflicts_detected": len(conflicts),
                    "unresolved_conflicts": len([c for c in conflicts if not c.resolved])
                }
            },
            "l1_paragraphs": [
                {
                    "id": p.id,
                    "source": p.source,
                    "section": p.section,
                    "raw_text": p.raw_text,
                    "semantic_unit": p.semantic_unit,
                    "sentences": [
                        {"id": s.id, "text": s.text, "role": s.role}
                        for s in p.sentences
                    ]
                }
                for p in paragraphs
            ],
            "l2_structured": {
                "functions": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "name_normalized": f.name_normalized,
                        "trigger": f.trigger,
                        "condition": f.condition,
                        "action": f.action,
                        "benefit": f.benefit,
                        "attributes": f.attributes,
                        "confidence": f.confidence,
                        "source_paragraphs": f.source_paragraphs,
                        "cross_references": f.cross_references,
                        "needs_review": f.needs_review
                    }
                    for f in structured.functions
                ]
            },
            "conflicts": [
                {
                    "id": c.id,
                    "type": c.type,
                    "severity": c.severity,
                    "field": c.field,
                    "values": c.values,
                    "resolved": c.resolved,
                    "final_value": c.final_value,
                    "needs_human": c.needs_human
                }
                for c in conflicts
            ],
            "actions": actions or [],
            "vision_analysis": references or []  # Vision LLM 分析结果
        }

        return json.dumps(data, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Commit**

```bash
git add skills/content-extractor/output/
git commit -m "feat(content-extractor): add Markdown and JSON output formatters"
```

---

## Task 12: Main Entry Point

**Files:**
- Create: `skills/content-extractor/main.py`

- [ ] **Step 1: Create main.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/main.py
git commit -m "feat(content-extractor): add main entry point orchestrator"
```

---

## Task 13: Package Init Files

**Files:**
- Create: All remaining `__init__.py` files

- [ ] **Step 1: Create all __init__.py files**

```python
# Create empty __init__.py files for all packages
touch skills/content-extractor/associator/__init__.py
touch skills/content-extractor/extractors/__init__.py
touch skills/content-extractor/dictionaries/__init__.py
touch skills/content-extractor/output/__init__.py
```

Actually, these should have content for proper imports:

**associator/__init__.py:**
```python
from .term_mapper import TermMapper
from .ref_linker import RefLinker
```

**extractors/__init__.py:**
```python
from .markdown_extractor import MarkdownExtractor
from .image_extractor import ImageExtractor
```

**output/__init__.py:**
```python
from .markdown_report import MarkdownReportGenerator
from .json_exporter import JSONExporter
```

- [ ] **Step 2: Commit**

```bash
git add skills/content-extractor/associator/__init__.py skills/content-extractor/extractors/__init__.py skills/content-extractor/output/__init__.py
git commit -m "chore(content-extractor): add remaining __init__.py files"
```

---

## Task 14: Test Suite

**Files:**
- Create: `tests/test_content_extractor.py`

- [ ] **Step 1: Create test file**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_content_extractor.py
git commit -m "test(content-extractor): add basic test suite"
```

---

## Summary

**Tasks Completed: 14** (Task 6 已更新)
**Total Files Created: ~25**

**MVP Capabilities:**
- Text/markdown input via clipboard or files
- Image OCR support (optional dependency)
- **Image Vision understanding via external MCP provider (p0)**
- L1 paragraph extraction with sentence roles
- L2 structured data with trigger/condition/action/benefit
- **Vision components → L2 Function 直接构建（绕过 MarkdownExtractor）**
- Term dictionary-based association
- Cross-document reference extraction
- **Vision analysis 完整保存到 JSON (`vision_analysis` refs)**
- Conflict detection with authority-based resolution
- Markdown report generation
- JSON structured output

**Dependencies to install:**
```bash
pip install pyyaml pillow pytesseract markdown-it
# Vision MCP (MiniMax or OpenAI Vision) 由 Agent 层通过 MCP 调用
```

**Next steps after MVP:**
1. Add PDF/Docx support (V1)
2. ~~Add URL handler for remote links~~ → 由 Agent 层 mcp__fetch__fetch 处理（已完成）
3. ~~Add LLM semantic enhancement~~ → 由 Vision MCP 处理（已完成，Task 6 更新）
4. Add entity alignment (V2)
5. 支持从 Vision components 直接构建 L2 Function（已在 Task 6 中实现）
6. PDF 解析器（P1 - 复用现有工具链）
