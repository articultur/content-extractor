# Content Extractor

Parses heterogeneous documents (text/markdown/files/images/PDF), extracts requirements, and associates them.

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
    - type: file
      path: ./docs/report.pdf   # PDF with embedded images supported
    - type: url
      url: https://example.com/doc.md
```

### Output

- Markdown report: `requirements-report.md`
- JSON structured: `requirements-report.json`
- Association graph: `requirements-graph.json`

## Supported Input Types

| Type | Format | Processing |
|------|--------|------------|
| Text | markdown / plain text | MarkdownExtractor |
| File | .md, .txt | MarkdownExtractor |
| File | .pdf | PDFExtractor → text + embedded images |
| File | .docx | DOCXExtractor → paragraphs + tables |
| File | .png, .jpg, .jpeg | ImageExtractor (OCR + Vision) |
| URL | .md, .markdown | URLHandler → fetch → MarkdownExtractor |
| URL | .pdf | URLHandler → fetch → PDFExtractor |
| URL | .png, .jpg, .jpeg | URLHandler → fetch → ImageExtractor (OCR + Vision) |
| URL | .html, other | URLHandler → fetch → HTML strip → MarkdownExtractor |

**URL type resolution:** URLHandler resolves type by file extension in URL path, with `Content-Type` header as fallback. Falls back to HTML for unknown extensions.

## Architecture

- L1: Paragraph index (preserves raw text)
- L2: Structured data (machine-readable)
- Three-layer association: term mapping → reference linking → entity alignment

## PDF Processing

PDF files are processed in two stages:
1. **Text extraction** — via pdfplumber (always available if pdfplumber installed)
2. **Image extraction** — via PyMuPDF (extracts embedded images as PNG)

Each embedded image in a PDF goes through:
- OCR (PaddleOCR) — for text within images
- Vision LLM — for semantic understanding of diagrams/UI/charts

Extracted images are processed as temporary files and cleaned up after use.

## Vision Pipeline

Images (from files, PDFs, or URLs) are processed through a two-layer extraction:

1. **OCR layer** (PaddleOCR) — extracts visible text from images
2. **Vision LLM layer** — semantic analysis of UI components, diagrams, and charts

Vision components are converted to L2 Function objects with:
- `trigger` — user interaction (e.g., "点击 Sign In 按钮")
- `name_normalized` — machine-readable identifier (e.g., `user_login`)
- `name` — display label (e.g., "Sign In")

## Architecture

- **L1**: Paragraph index — preserves `raw_text`, section headers, sentence roles (trigger/condition/action/result)
- **L2**: Structured Function objects — machine-readable with trigger/condition/action/benefit fields
- **Three-layer association**: term mapping → reference linking → entity alignment
- **Graph output**: Function associations written to `requirements-graph.json`

## Dependencies

- `pdfplumber` - PDF text extraction (required for PDF support)
- `PyMuPDF` (fitz) - PDF image extraction (optional, enables embedded image processing)
- `python-docx` - DOCX text extraction (optional, enables .docx support)
- `Pillow` - Image processing for OCR pre-processing
- `anthropic` / `openai` / Vision MCP - LLM providers for Vision analysis

