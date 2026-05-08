"""Native WhatsApp list UI rows (interactive message) — richer than plaintext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# WhatsApp interactive list caps (approximate conservative limits).
ROW_TITLE_MAX = 24
ROW_DESCR_MAX = 72


@dataclass(frozen=True)
class InteractiveListRow:
    """Maps to WhatsApp interactive `rows[].id|title|description`."""

    row_id: str
    title: str
    description: str


def _clip(s: str, n: int) -> str:
    t = " ".join((s or "").strip().split())
    return t if len(t) <= n else t[: n - 1] + "…"


def job_pick_rows_native_list(jobs: list[dict[str, Any]]) -> tuple[InteractiveListRow, ...]:
    """Turn search_jobs catalogue entries into WhatsApp-native list rows (max 10)."""
    real = [j for j in jobs if isinstance(j, dict) and j.get("id") and not j.get("note")]
    out: list[InteractiveListRow] = []
    for j in real[:10]:
        jid = str(j.get("id", "")).strip()
        role = _clip(str(j.get("title", "Role")), ROW_TITLE_MAX)
        company = str(j.get("company", "")).strip()
        fit = str(j.get("fit_label", "")).strip()
        tags = j.get("tags")
        hint = ""
        if isinstance(tags, list) and tags:
            hint = _clip(" · ".join(str(t) for t in tags[:3]), ROW_DESCR_MAX)
        descr_bits = [_clip(company, 22), fit, hint]
        descr = _clip(" · ".join(x for x in descr_bits if x), ROW_DESCR_MAX)
        if not descr.strip():
            descr = _clip(str(j.get("why", "")) or jid, ROW_DESCR_MAX)
        rid = f"job_{jid}"[:199]
        out.append(InteractiveListRow(row_id=rid, title=role or _clip(jid, ROW_TITLE_MAX), description=descr))
    return tuple(out)


def prelude_and_outro_for_native_list(final_assistant_text: str, footer: str) -> tuple[str | None, tuple[str, ...]]:
    """Intro before list + closing hints after."""
    from mitra_api.whatsapp.job_cards import WHATSAPP_CARD_FOOTER_DEFAULT, WHATSAPP_SHORTLIST_MARKER

    ft = (final_assistant_text or "").strip()
    foot = (footer or "").strip() or WHATSAPP_CARD_FOOTER_DEFAULT
    intro = None
    if WHATSAPP_SHORTLIST_MARKER in ft:
        intro = ft.split(WHATSAPP_SHORTLIST_MARKER, 1)[0].strip()
    return (intro or None), (foot,)



