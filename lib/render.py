"""Render raw HTML as clean readable markdown using readability-lxml + markdownify."""
import re

from readability import Document
from markdownify import markdownify


def html_to_markdown(html: str, url: str = "") -> str:
    """Extract main content from HTML and convert to clean markdown."""
    doc = Document(html, url=url)
    clean_html = doc.summary()
    title = doc.short_title()

    md = markdownify(clean_html, heading_style="ATX", strip=["img", "script", "style"])

    # collapse excessive blank lines
    md = re.sub(r'\n{3,}', '\n\n', md)

    return md.strip()
