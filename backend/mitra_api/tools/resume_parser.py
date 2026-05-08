"""
mitra_api/tools/resume_parser.py

Parses a PDF resume sent via WhatsApp into structured candidate signals.

Flow
----
1. Twilio webhook receives a media message (PDF)
2. Orchestrator calls parse_resume_from_url() automatically (no LLM tool call needed)
3. PDF text extracted with pypdf
4. Configured LLM (OpenAI / Anthropic) extracts structured signals
5. Signals persisted; orchestrator injects summary + missing fields into system context
6. Agent reacts naturally and asks targeted follow-up questions
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

import httpx

from mitra_api.config import get_settings

log = logging.getLogger(__name__)

# Signals that should come from conversation, not resume
_CONVERSATION_SIGNALS = {
    "motivation", "salary_floor_lpa", "salary_target_lpa",
    "startup_stage_pref", "dealbreakers", "actively_looking",
    "notice_period_days", "location_preference",
}

# Ordered list of which missing signals to ask about first
_FOLLOW_UP_PRIORITY = [
    ("motivation",          "why they're looking to move right now"),
    ("salary_floor_lpa",    "their salary expectation (in LPA)"),
    ("location_preference", "their preferred location or remote preference"),
    ("startup_stage_pref",  "which startup stages they're open to"),
    ("notice_period_days",  "their notice period"),
]

_EXTRACT_SYSTEM = """You are extracting structured information from a resume.
Return ONLY a valid JSON object — no markdown fences, no preamble, no trailing text.

Extract these keys (omit any key where the information is not clearly stated):

{
  "candidate_name":          "Full name",
  "current_role":            "Most recent job title",
  "current_company":         "Most recent employer",
  "years_experience":        <integer — total years of professional experience>,
  "primary_stack":           ["main", "technologies", "frameworks", "languages"],
  "education":               "Highest / most relevant degree and institution",
  "notable_projects":        "1-2 sentences on the most impressive project or achievement",
  "previous_companies":      ["list of prior employers, most recent first"],
  "has_startup_experience":  <true | false>,
  "has_leadership_experience": <true | false>,
  "location":                "City/country if mentioned",
  "linkedin":                "LinkedIn URL if present",
  "github":                  "GitHub URL if present"
}

Rules:
- Be conservative. Only include facts clearly stated in the resume.
- Do NOT infer years_experience from graduation year — only count stated work experience.
- primary_stack should list actual technologies used, not job titles.
- If a field is absent or unclear, omit it entirely — do not guess."""


async def parse_resume_from_bytes(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract structured candidate signals from raw PDF bytes.
    Uses the configured LLM provider (OpenAI or Anthropic).
    Returns a signals dict compatible with remember_candidate_signals.
    """
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        ).strip()
    except Exception:
        log.exception("PDF text extraction failed")
        return {}

    if not text or len(text) < 50:
        log.warning("PDF yielded too little text (%d chars) — may be image-based", len(text))
        return {}

    text = text[:8000]

    s = get_settings()

    try:
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage

        adapter = get_llm_adapter(s)
        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_EXTRACT_SYSTEM),
                ChatMessage(role="user",   content=f"RESUME:\n{text}"),
            ],
            tools=None,
            max_tokens=800,
            temperature=0.0,
        )

        raw = (result.content or "").strip()
        # Strip markdown fences if the model added them
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        signals = json.loads(raw)
        if not isinstance(signals, dict):
            return {}

        # Remove null / empty values
        signals = {k: v for k, v in signals.items() if v not in (None, "", [], {})}

        log.info("Parsed resume — %d signals: %s", len(signals), sorted(signals.keys()))
        return signals

    except Exception:
        log.exception("Resume parsing LLM call failed")
        return {}


def missing_follow_up_questions(extracted: dict[str, Any], existing: dict[str, Any]) -> list[str]:
    """
    Given what was extracted from the CV and what's already in the session,
    return an ordered list of labels for signals still missing that the agent
    should ask about (one at a time).
    """
    all_known = {**existing, **extracted}
    missing = []
    for key, label in _FOLLOW_UP_PRIORITY:
        if not all_known.get(key):
            missing.append(label)
    return missing


async def parse_resume_from_url(url: str, *, auth_headers: dict | None = None) -> dict[str, Any]:
    """Download a PDF from a URL and parse it."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        log.warning("parse_resume_from_url: invalid URL %r — skipping", url[:80])
        return {}

    headers = auth_headers or {}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            pdf_bytes = resp.content
    except Exception:
        log.exception("Failed to download resume from %s", url[:80])
        return {}

    return await parse_resume_from_bytes(pdf_bytes)


def twilio_media_auth(settings) -> dict[str, str]:
    """Build Basic auth header for downloading Twilio media."""
    import base64
    creds = f"{settings.twilio_account_sid}:{settings.twilio_auth_token}"
    encoded = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}
