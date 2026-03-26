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

## Supported Input Types

| Type | Format | Processing |
|------|--------|------------|
| Text | markdown / plain text | MarkdownExtractor |
| File | .md, .txt | MarkdownExtractor |
| File | .pdf | PDFExtractor → text + images |
| File | .png, .jpg, .jpeg | ImageExtractor (OCR + Vision) |
| URL | http(s):// | URLHandler → content-type parser |

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

## Dependencies

- `pdfplumber` - PDF text extraction (required for PDF support)
- `PyMuPDF` (fitz) - PDF image extraction (optional, enables embedded image processing)
- `Pillow` - Image processing for OCR pre-processing
- `anthropic` / `openai` / Vision MCP - LLM providers for Vision analysis

