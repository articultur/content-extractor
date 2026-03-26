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
        """Extract text from PDF file. Returns list of page texts."""
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
        """Extract full content with metadata."""
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
