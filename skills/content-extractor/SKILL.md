# Content Extractor

Parses heterogeneous documents (text/markdown/files/images/PDF/DOCX/URL) and extracts structured requirements for test document generation. Triggers when user provides documents, URLs, or pasted content for analysis — especially when they want to understand requirements structure, extract trigger/condition/action/benefit fields, or build a requirements knowledge graph.

## Usage

### Input Methods

**1. Text Paste (in conversation)**
Paste markdown or text content directly using `--text`:
```bash
python main.py --text "# Login\n\nUser logs in. System validates password."
```

**2. Config File**
```yaml
input:
  documents:
    - type: text
      content: |
        # Login
        User logs in with password.
        System validates credentials.
    - type: file
      path: ./docs/requirements.md
    - type: file
      path: ./docs/report.pdf   # PDF with embedded images supported
    - type: file
      path: ./docs/spec.docx    # DOCX with tables supported
    - type: url
      url: https://example.com/doc.md
```

### Output

| File | Description |
|------|-------------|
| `requirements-report.md` | Markdown format requirements report |
| `requirements-report.json` | Structured JSON (L1 paragraphs + L2 functions + conflicts + references) |
| `requirements-graph.json` | Function association graph (nodes + edges with confidence weights) |

## Supported Input Types

| Type | Format | Processing |
|------|---------|------------|
| Text | markdown / plain text | ClipboardHandler detects type → MarkdownExtractor |
| Text | `--text` inline flag | ClipboardHandler detects type → MarkdownExtractor |
| File | .md, .txt | MarkdownExtractor |
| File | .pdf | PDFExtractor → text + embedded images |
| File | .docx | DOCXExtractor → paragraphs + tables |
| File | .png, .jpg, .jpeg | ImageExtractor (OCR + Vision) |
| URL | .md, .markdown | URLHandler → fetch → MarkdownExtractor |
| URL | .pdf | URLHandler → fetch → PDFExtractor |
| URL | .png, .jpg, .jpeg | URLHandler → fetch → ImageExtractor (OCR + Vision) |
| URL | .html, other | URLHandler → fetch → HTML strip → MarkdownExtractor |

**URL type resolution:** URLHandler resolves type by file extension in URL path, with `Content-Type` header as fallback. Falls back to HTML for unknown extensions.

**Text routing:** `ClipboardHandler.parse()` auto-detects markdown indicators (`#`, ` ``` `, `-`, `**`, etc.) and routes as `"markdown"` or `"text"` — both go to MarkdownExtractor but the routing is tracked in `all_sources`.

## Processing Pipeline

```
Source Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Processor Layer                                         │
│  MarkdownExtractor → L1 Paragraphs (section, sentences)  │
│  PDFExtractor → text + embedded images                   │
│  DOCXExtractor → paragraphs + tables                     │
│  ImageExtractor → OCR text + Vision analysis             │
│  VisionMapper → Vision JSON → L2 Function              │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Association Layer                                       │
│  TermMapper → terminology normalization (Jaccard)        │
│  RefLinker → cross-document refs (URLs, "第X章")      │
│  EntityAligner → fuzzy entity merge (Chinese↔English)  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Merge & Conflict Layer                                 │
│  EntityAligner.merge_duplicates()                      │
│    merges functions with similar names, combines         │
│    source_paragraphs, removes duplicates               │
│  ConflictResolver.detect_conflicts()                   │
│    detects same-name functions with different fields   │
│  ConflictResolver.resolve_conflicts()                 │
│    auto-resolve by authority priority                 │
│    separates needs_human=True → for human review        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Graph Builder                                         │
│  RefLinker.resolve_reference() → links cross-refs     │
│  TermMapper associations → links related functions      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Output: requirements-report.md / .json / -graph.json
```

## Data Model: L1 → L2

```
L1 Paragraph                          L2 Function
─────────────────────                ──────────────────────────────────────
Paragraph.id          ───────────▶    Function.id
Paragraph.section     ───────────▶    Function.name
Paragraph.raw_text    ───────────▶    Function.name_normalized (via TermMapper)
Sentence.role=trigger ───────────▶    Function.trigger
Sentence.role=condition ──────────▶    Function.condition
Sentence.role=action  ───────────▶    Function.action
Sentence.role=result   ───────────▶    Function.benefit
                                     Function.confidence (dynamic, source-based)
                                     Function.source_paragraphs
```

## Three-layer Association

```
Layer 1 — TermMapper
  Normalize terms (Chinese/English synonyms) → Jaccard-based association

Layer 2 — RefLinker
  Extract explicit references (URLs, "见第3节", "第三章", "详见...") from raw text

Layer 3 — EntityAligner
  Fuzzy match Function entities across sources (edit distance + normalization)
  Used for merge_duplicates before conflict detection
```

## Conflict Detection & Resolution

ConflictResolver detects field value conflicts between functions with the same normalized name:

- **Authority-based auto-resolution**: When two sources have different authority scores (e.g., "产品经理" > "开发"), the higher authority wins automatically and `final_value` is set.
- **Equal authority → human review**: When authority scores are equal, `needs_human=True` and the conflict is passed through to the report for manual resolution.

Authority priority: `甲方 > 产品经理/需求文档 > 开发 > 测试 > LLM > unknown`

## Confidence Scoring

Dynamic confidence based on source type and content quality:

| Source | Base Confidence |
|--------|----------------|
| Text / Markdown | 0.95 |
| PDF / DOCX | 0.90 |
| Image (OCR) | 0.85 |
| Vision LLM | 0.80 |

Quality adjustments: section header (+0.03), trigger-action pair (+0.03), trigger-condition-action (+0.05), short/empty content (-0.05).

## PDF Processing

PDF files are processed in two stages:
1. **Text extraction** — via pdfplumber
2. **Image extraction** — via PyMuPDF (extracts embedded images as PNG)

Each embedded image then goes through OCR + Vision pipeline. Temporary image files are cleaned up after processing.

## Image Processing (OCR + Vision)

Images are processed through two layers:

1. **OCR layer** — pytesseract with English + Chinese language support
   - External OCR provider can be registered via `ImageExtractor.set_ocr_provider()`
   - Graceful fallback: if OCR fails, continues with Vision only

2. **Vision layer** — External MCP/LLM provider (required for semantic understanding)
   - `ImageExtractor.set_vision_provider()` registers the vision callable
   - Timeout: 60 seconds per image
   - Retry: up to 2 attempts on failure (exponential backoff: 1s, 2s)
   - Vision converts UI components, diagrams, charts to L2 Function objects

Vision components become Functions with:
- `trigger`: user interaction (e.g., "点击 Sign In 按钮")
- `name_normalized`: machine-readable ID (e.g., `user_login`)
- `name`: display label (e.g., "Sign In")

## Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `pdfplumber` | PDF text extraction | Yes (for PDF support) |
| `PyMuPDF` (fitz) | PDF image extraction | Optional (enables embedded images) |
| `python-docx` | DOCX text extraction | Optional (enables .docx support) |
| `pytesseract` | OCR engine | Optional (enables image text extraction) |
| `Pillow` | Image processing | Optional (required by pytesseract) |
| Vision MCP / LLM | Semantic image understanding | Optional (enables Vision layer) |

Install optional dependencies: `pip install python-docx pytesseract pillow`
