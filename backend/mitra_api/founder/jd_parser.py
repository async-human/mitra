"""
mitra_api/founder/jd_parser.py

Extract hiring signals from a PDF or DOCX job description.

Flow
----
1. Read raw bytes from the uploaded file
2. Extract plain text (pypdf for PDF, python-docx for DOCX/DOC)
3. Call the configured LLM with a structured extraction prompt
4. Return a signals dict with the same keys the founder chat uses
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

from mitra_api.config import Settings
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage

log = logging.getLogger(__name__)

# Keys must match the signal keys used throughout the founder onboarding flow
_EXTRACT_SYSTEM = """You are extracting structured hiring information from a job description.

Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.
Omit any key where the information is not clearly present. Do not infer or embellish.

## CRITICAL EXTRACTION RULES — read before extracting:

1. **role_title**: Copy the job title EXACTLY as written, including any parenthetical specialization.
   CORRECT:   "Senior AI Engineer (Agentic AI)" → "Senior AI Engineer (Agentic AI)"
   INCORRECT: splitting it into title="Senior AI Engineer" and company="Agentic AI"
   A word in parentheses inside a job title is a domain/specialization — NOT a company name.

2. **company_name**: Find it in the "About Us" section, document header, letterhead, or company introduction.
   NEVER extract company_name from words inside the job title.
   If the JD says "About Acme Corp" or "We are building at Acme Corp" — that is the company.
   If company name is genuinely absent, omit this key entirely.

3. When in doubt about any field, omit it — never guess or infer.

## CORE KEYS — use exactly these names when the information is present:

"role_title"      — full job title verbatim (including any parenthetical domain/specialization)
"company_name"    — company name from About section or header (NOT from the job title)
"stage"           — funding stage: Seed / Series A / Series B / bootstrapped / etc.
"location"        — city and remote policy, e.g. "Bengaluru (hybrid)" or "Remote"
"salary_range"    — compensation in LPA, e.g. "25–40 LPA"
"first_90_days"   — what this person will own and deliver (from responsibilities)
"dealbreaker"     — hard requirements / must-haves
"culture_signal"  — team culture, values, working style
"why_join"        — what makes this company or role exciting

## ADDITIONAL KEYS — also extract any other relevant information using concise snake_case keys.

Common examples (use these exact names when applicable):
"stack"                  — technologies, languages, frameworks required, as a comma-separated string
"equity"                 — ESOP / equity offer, e.g. "0.1–0.5% over 4 years"
"sector"                 — industry vertical, e.g. "Fintech", "B2B SaaS", "Developer Tools"
"team_size"              — engineering team headcount or overall company size
"years_exp_required"     — minimum years of experience required
"reporting_to"           — who this role reports to, e.g. "CTO" or "Founding Engineer"
"interview_process"      — number of rounds, format, take-home, etc.
"benefits"               — perks, leave policy, health insurance, WFH allowance, etc.
"hiring_urgency"         — timeline or urgency signal, e.g. "immediate joiner preferred"
"headcount_plan"         — how many people they're hiring for this role

For any other relevant information not covered above, invent a descriptive snake_case key.
Every value must be a plain string (not a list or object)."""


async def extract_text_from_pdf(data: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception:
        log.exception("PDF text extraction failed")
        return ""


async def extract_text_from_docx(data: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        log.exception("DOCX text extraction failed")
        return ""


async def extract_jd_text(data: bytes, filename: str) -> str:
    """Dispatch to the right extractor based on file extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return await extract_text_from_pdf(data)
    if name.endswith(".docx") or name.endswith(".doc"):
        return await extract_text_from_docx(data)
    # Unknown type — try PDF first, then DOCX
    text = await extract_text_from_pdf(data)
    if not text:
        text = await extract_text_from_docx(data)
    return text


async def extract_jd_signals(text: str, settings: Settings) -> dict[str, Any]:
    """
    Call the LLM to extract structured hiring signals from raw JD text.
    Returns a dict with founder-signal keys, or {} on failure.
    """
    if not text or len(text) < 30:
        log.warning("JD text too short to parse (%d chars)", len(text))
        return {}

    # Trim to keep tokens manageable while preserving full JD content
    truncated = text[:8000]

    adapter = get_llm_adapter(settings)
    try:
        result = await adapter.complete(
            model=settings.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_EXTRACT_SYSTEM),
                ChatMessage(role="user",   content=f"JOB DESCRIPTION:\n\n{truncated}"),
            ],
            tools=None,
            max_tokens=1024,
            temperature=0.0,
        )
    except Exception:
        log.exception("JD extraction LLM call failed")
        return {}

    raw = (result.content or "").strip()
    if not raw:
        log.warning("LLM returned empty response for JD extraction")
        return {}

    # Strip markdown fences if the model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
        if "```" in raw:
            raw = raw[: raw.index("```")]

    try:
        signals = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Could not parse LLM JD extraction response as JSON: %s", raw[:200])
        return {}

    if not isinstance(signals, dict):
        return {}

    # Flatten any nested values to strings (the session store expects str values)
    clean: dict[str, Any] = {}
    for k, v in signals.items():
        if v is None:
            continue
        clean[str(k)] = str(v) if not isinstance(v, str) else v

    log.info("JD extraction: found %d signals — %s", len(clean), list(clean.keys()))
    return clean
