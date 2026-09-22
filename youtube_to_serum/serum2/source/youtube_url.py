"""Shared YouTube video-id extraction.

Single implementation, used everywhere a YouTube URL needs its video_id
pulled out. Covers watch/shorts/youtu.be/embed/live URL forms.
"""
from __future__ import annotations

import re

_VIDEO_ID_PATTERNS = [
    r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
    r"youtube\.com/live/([A-Za-z0-9_-]{11})",
    r"[?&]v=([A-Za-z0-9_-]{11})",
    r"youtu\.be/([A-Za-z0-9_-]{11})",
]


def extract_youtube_video_id(url: str) -> str:
    """Extract the 11-character YouTube video ID from a URL.

    Raises ValueError if the URL doesn't match a recognized YouTube form.
    """
    for pattern in _VIDEO_ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError("Cannot extract video ID from URL: %r" % url[:80])
