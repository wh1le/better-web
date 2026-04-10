"""HTML structural signals: link density, ad scripts, code blocks."""
import re

from lib.settings import settings


def html_signals(html: str, text: str) -> tuple[int, list[str], dict]:
    """Score based on HTML structure. Returns (points, flags, details)."""
    points = 0
    flags: list[str] = []
    details: dict[str, object] = {}

    html_lower = html.lower()
    text_len = max(len(text), 1)

    # code blocks
    code_blocks = len(re.findall(r'<code[\s>]', html_lower))
    pre_blocks = len(re.findall(r'<pre[\s>]', html_lower))
    total_code = code_blocks + pre_blocks
    if total_code >= 2:
        points += 10
        flags.append("has_code")
    elif total_code == 1:
        points += 5
        flags.append("has_code")
    details["code_blocks"] = total_code

    # article tag
    if '<article' in html_lower:
        points += 3
        flags.append("has_article_tag")

    # comment/reply sections
    comment_markers = re.findall(r'class="[^"]*comment[^"]*"', html_lower)
    if len(comment_markers) >= 3:
        points += 5
        flags.append("has_comments")
        details["comment_sections"] = len(comment_markers)

    # link density
    link_count = len(re.findall(r'<a[\s>]', html_lower))
    density: float = link_count / (text_len / 100)
    details["link_density"] = round(density, 2)
    if density > 3.0:
        points -= 10
        flags.append("high_link_density")
    elif density > 2.0:
        points -= 5

    # nav-to-content ratio
    nav_len = sum(len(m) for m in re.findall(r'<nav[\s>].*?</nav>', html_lower, re.DOTALL))
    if nav_len > 0:
        nav_ratio: float = nav_len / max(len(html), 1)
        details["nav_ratio"] = round(nav_ratio, 3)
        if nav_ratio > 0.3:
            points -= 5
            flags.append("nav_heavy")

    # ad/tracker scripts
    ad_patterns = [t for t in settings.ad_trackers if t in html_lower]
    details["ad_scripts"] = len(ad_patterns)
    if len(ad_patterns) >= 4:
        points -= 5
        flags.append("ad_heavy")

    return points, flags, details
