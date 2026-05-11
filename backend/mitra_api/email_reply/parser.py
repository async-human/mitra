"""
mitra_api/email_reply/parser.py

Extract plain-text reply body from a raw MIME email string.
Uses Python's built-in email module — no extra dependencies.
Strips quoted/forwarded sections so the agent only sees new content.
"""
from __future__ import annotations

import email
import re
from email import policy

# Patterns that mark the beginning of quoted / forwarded content
_QUOTE_HEADERS = [
    re.compile(r"^On .{10,200} wrote:\s*$",                    re.MULTILINE),
    re.compile(r"^-+\s*(Original|Forwarded) Message\s*-+",     re.MULTILINE | re.IGNORECASE),
    re.compile(r"^From:\s+mitra@mitralabs\.co",                re.MULTILINE | re.IGNORECASE),
    re.compile(r"^_{3,}",                                       re.MULTILINE),
    re.compile(r"^Sent from ",                                  re.MULTILINE | re.IGNORECASE),
]


def extract_reply_text(raw_email: str) -> str:
    """
    Parse a raw MIME email string and return the plain-text reply body,
    with quoted / forwarded sections stripped.
    Falls back to a truncated slice of the raw string if parsing fails.
    """
    try:
        msg  = email.message_from_string(raw_email, policy=policy.default)
        part = msg.get_body(preferencelist=("plain",))
        if part:
            text = part.get_content()
        else:
            # Try HTML and strip tags
            part = msg.get_body(preferencelist=("html",))
            text = re.sub(r"<[^>]+>", " ", part.get_content()) if part else ""

        return _strip_quoted(text or "").strip()
    except Exception:
        return raw_email[:1500].strip()


def _strip_quoted(text: str) -> str:
    """Cut everything from the first quote-separator line onwards."""
    cut = len(text)
    for pattern in _QUOTE_HEADERS:
        m = pattern.search(text)
        if m and m.start() < cut:
            cut = m.start()

    # Also drop lines that begin with ">" (inline quoting)
    lines = text[:cut].splitlines()
    clean = [line for line in lines if not line.startswith(">")]
    return "\n".join(clean)
