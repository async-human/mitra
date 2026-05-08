"""WhatsApp job card layouts — elegant inline cards using WhatsApp native text formatting.

Design principles:
  - Each job is its own WhatsApp bubble (separate message) for clean visual separation
  - Bold for role title and company, italic for supporting details
  - Clear visual hierarchy: role -> company -> fit -> tags -> why -> CTA
  - No monospace blocks — WhatsApp renders bold/italic inline cards much more cleanly
  - Dividers use Unicode dashes for a refined look without monospace
  - CTA is clear and actionable at the bottom of every card
"""

from __future__ import annotations

import textwrap
from typing import Any

WHATSAPP_SHORTLIST_MARKER = "*Your shortlist*"
WHATSAPP_CARD_FOOTER_DEFAULT = (
    "_Reply with the number of the role you want an intro to, "
    "or tell me what to adjust._"
)

_FIT_STARS = {
    range(95, 101): "★★★★★",
    range(88, 95):  "★★★★☆",
    range(80, 88):  "★★★☆☆",
}


def _fit_stars(fit_label: str) -> str:
    try:
        pct = int("".join(c for c in fit_label if c.isdigit()))
        for r, stars in _FIT_STARS.items():
            if pct in r:
                return stars
    except (ValueError, TypeError):
        pass
    return "★★★☆☆"


def _wrap_why(text: str, width: int = 38, max_lines: int = 3) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    lines = textwrap.wrap(t, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip()
        if not lines[-1].endswith("…"):
            lines[-1] += "…"
    return "\n".join(lines)


def format_single_job_whatsapp_segment(job: dict[str, Any], idx: int, total: int) -> str:
    """
    Render a single job as an elegant inline WhatsApp card.

    Visual structure (each card is its own bubble):

        ―――――――――――――――――――――――――
        *1 of 3*  ·  ★★★★☆  _94% fit_

        *Senior Backend Engineer*
        _Setu · Series B · Fintech_

        Remote · India  ·  Python  ·  FastAPI

        Owns payment reconciliation APIs
        serving 2M txns/day. High-ownership
        role reporting directly to CTO.

        Reply *1* to get introduced  →
        ―――――――――――――――――――――――――
    """
    title   = str(job.get("title",    "Role")).strip()
    company = str(job.get("company",  "")).strip()
    loc     = str(job.get("location", "")).strip()
    why     = str(job.get("why",      "")).strip()
    fit     = str(job.get("fit_label","")).strip()
    tags    = job.get("tags")

    if not isinstance(tags, list):
        tags = []
    tag_strs = [str(t).strip() for t in tags if str(t).strip()]

    tag_line  = "  ·  ".join(tag_strs[:3]) if tag_strs else loc or ""
    stars     = _fit_stars(fit)
    why_block = _wrap_why(why)
    job_id    = str(job.get("external_id") or job.get("id") or idx)
    cta       = f"Reply *{idx}* to get introduced  →  `{job_id}`"
    divider   = "\u2015" * 25  # ― repeated

    lines: list[str] = [
        divider,
        f"*{idx} of {total}*  ·  {stars}  _{fit}_",
        "",
        f"*{title}*",
    ]

    if company:
        lines.append(f"_{company}_")

    if tag_line:
        lines.append("")
        lines.append(tag_line)

    if why_block:
        lines.append("")
        lines.append(why_block)

    lines.extend([
        "",
        cta,
        divider,
    ])

    return "\n".join(lines)


def build_search_jobs_tool_payload(
    picks: list[dict[str, Any]],
    *,
    query_echo: Any = None,
) -> dict[str, Any]:

    if not picks:
        return {
            "jobs": [],
            "formatted_cards": "_Nothing strong matched yet — try widening your stack or location._",
            "whatsapp_segments": None,
            "whatsapp_footer": "",
            "presentation_note": "",
            "query_echo": query_echo,
        }

    if len(picks) == 1 and picks[0].get("note"):
        sug = str(picks[0].get("suggestion") or "").strip()
        msg = (
            f"_No strong matches in the catalogue yet._\n\n*Tip:* {sug}"
            if sug
            else "_No strong matches in the catalogue yet._ Try rephrasing your ideal role."
        )
        return {
            "jobs": picks,
            "formatted_cards": msg,
            "whatsapp_segments": None,
            "whatsapp_footer": "",
            "presentation_note": "Reply with one brief tip to broaden their search.",
            "query_echo": query_echo,
        }

    job_rows = [j for j in picks if not j.get("note")]
    n        = len(job_rows)

    segments = [
        format_single_job_whatsapp_segment(j, i, n)
        for i, j in enumerate(job_rows, start=1)
    ]

    body            = "\n\n".join(segments)
    formatted_cards = f"{WHATSAPP_SHORTLIST_MARKER}\n\n{body}\n\n{WHATSAPP_CARD_FOOTER_DEFAULT}"

    return {
        "jobs": picks,
        "query_echo": query_echo,
        "formatted_cards": formatted_cards,
        "whatsapp_segments": segments,
        "whatsapp_footer": WHATSAPP_CARD_FOOTER_DEFAULT,
        "presentation_note": (
            "Paste `formatted_cards` verbatim in your assistant message. "
            f"Add a personalised line *above* '{WHATSAPP_SHORTLIST_MARKER}' only. "
            "Each role will be sent as its own WhatsApp bubble. "
            "When the candidate selects a role, call request_intro with the job's `id` field from the `jobs` array above."
        ),
    }


def whatsapp_outbound_chain(
    *,
    assistant_final_text: str,
    search_segments: list[str] | None,
    search_footer: str | None,
) -> list[str]:
    raw      = (assistant_final_text or "").strip()
    segments = [s.strip() for s in (search_segments or []) if s and str(s).strip()]
    footer   = (search_footer or "").strip() or WHATSAPP_CARD_FOOTER_DEFAULT

    if not segments:
        return [raw] if raw else []

    intro = ""
    if WHATSAPP_SHORTLIST_MARKER in raw:
        intro = raw.split(WHATSAPP_SHORTLIST_MARKER, 1)[0].strip()

    out: list[str] = []
    if intro:
        out.append(intro)
    out.extend(segments)
    out.append(footer)
    return [p for p in out if p.strip()]