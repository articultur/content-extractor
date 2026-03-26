"""Handle remote URL input."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class URLHandler:
    """Handles remote URL input and type resolution."""

    URL_TYPE_PATTERNS = {
        "pdf": [r"\.pdf$", r"/[^/]+\.pdf", r"\?.*\.pdf"],
        "markdown": [r"\.md$", r"\.markdown$", r"\.mdown$"],
        "html": [r"\.html?$", r"\.htm$"],
        "image": [r"\.(png|jpg|jpeg|gif|bmp|webp)$"],
        "docx": [r"\.docx$"],
    }

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

        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(path))

    def resolve_type(self, url: str) -> str:
        """Resolve URL to content type based on extension."""
        url_lower = url.lower()

        for content_type, patterns in self.URL_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return content_type

        return "html"

    def get_parser_type(self, url: str) -> str:
        """Get the appropriate parser type for URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for key, parser in self.DOMAIN_PARSERS.items():
            if key in domain:
                return parser

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