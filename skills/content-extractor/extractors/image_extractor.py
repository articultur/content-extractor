"""Extract text from images using OCR."""

from typing import Optional
import os

# Optional import - will work without pytesseract but warn user
try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


class ImageExtractor:
    """Extracts text from images using OCR."""

    def extract(self, image_path: str) -> Optional[str]:
        """
        Extract text from image using OCR.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text or None if OCR unavailable
        """
        if not HAS_OCR:
            print("Warning: OCR not available. Install pytesseract and tesseract.")
            return None

        if not os.path.exists(image_path):
            return None

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='eng+chi')
            return text.strip()
        except Exception as e:
            print(f"OCR failed for {image_path}: {e}")
            return None

    def extract_with_metadata(self, image_path: str) -> dict:
        """Extract text and image metadata."""
        text = self.extract(image_path)

        return {
            "ref": image_path,
            "type": "image",
            "ocr_text": text or "",
            "has_text": bool(text),
            "needs_vision_model": not text,  # Flag for LLM if OCR fails
            "visual_note": f"Extracted {len(text) if text else 0} characters"
        }
