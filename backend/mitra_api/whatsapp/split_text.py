"""Split assistant replies for WhatsApp text limits (session messages up to ~4096 chars)."""


def split_whatsapp_text(text: str, max_chars: int = 4000) -> list[str]:
    """
    Prefer splitting on blank lines; avoids mid-UTF-8 surrogate issues (plain str slice).
    Keeps each segment under max_chars with a small safety margin vs 4096.
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
