"""Split assistant replies for WhatsApp text limits.

Twilio WhatsApp: 1600 chars/segment hard limit.
Meta Cloud API: 4096 chars/segment.
Default is 1500 — safe for both channels with a comfortable margin.
"""


def split_whatsapp_text(text: str, max_chars: int = 1500) -> list[str]:
    """
    Prefer splitting on blank lines; avoids mid-UTF-8 surrogate issues (plain str slice).
    Keeps each segment under max_chars — default 1500 is safe for Twilio (hard cap 1600).
    """
    t = text.strip()
    if len(t) <= max_chars:
        return [t]

    parts: list[str] = []
    rest = t
    while rest:
        if len(rest) <= max_chars:
            parts.append(rest)
            break
        chunk = rest[:max_chars]
        cut = chunk.rfind("\n\n")
        if cut < max_chars // 3:
            cut = chunk.rfind("\n")
        if cut < max_chars // 3:
            cut = max_chars
        piece = rest[:cut].rstrip()
        if not piece:
            piece = rest[:max_chars]
            cut = len(piece)
        parts.append(piece)
        rest = rest[cut:].lstrip()

    return parts
