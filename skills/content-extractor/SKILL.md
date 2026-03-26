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

## Dependencies

- `pdfplumber` - PDF text extraction (optional, falls back gracefully if not installed)
- `Pillow` - Image processing for OCR pre-processing
- `anthropic` / `openai` - LLM providers for Vision analysis
