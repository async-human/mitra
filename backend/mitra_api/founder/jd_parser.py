"""
mitra_api/founder/jd_parser.py

Extract hiring signals from a PDF or DOCX job description.

Flow
----
1. Read raw bytes from the uploaded file
2. Extract plain text (pypdf for PDF, python-docx for DOCX/DOC)
3. Call the configured LLM with a structured extraction prompt
4. Return a signals dict — string fields for the session store,
   list fields for rendering (stored as JSON strings in session store)
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

_EXTRACT_SYSTEM = """You are extracting structured hiring information from a job description.

Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.
Omit any key where the information is not clearly present. Do not infer or embellish.

## CRITICAL EXTRACTION RULES:

1. **role_title**: Copy the job title EXACTLY as written, including any parenthetical specialization.
   CORRECT:   "Senior AI Engineer (Agentic AI)" → "Senior AI Engineer (Agentic AI)"
   INCORRECT: splitting it into title="Senior AI Engineer" and company="Agentic AI"

2. **company_name**: Find it in "About Us", document header, letterhead, or company intro.
   NEVER extract company_name from words inside the job title.

3. When in doubt about any field, omit it — never guess or infer.

## REQUIRED KEYS (strings):

"role_title"         — Full job title verbatim (including parenthetical domain/specialization)
"company_name"       — Company name from About section or header (NOT from job title)
"location"           — City and remote policy, e.g. "Hybrid - Pune, Gurugram, Bengaluru" or "Remote"
"work_type"          — Exactly one of: "Remote" | "Hybrid" | "In-office"
"salary_range"       — Compensation, e.g. "₹30–35L/yr" or "25–40 LPA"
"experience_range"   — e.g. "6–11 yrs" or "5+ years"
"industry"           — Industry sector, e.g. "IT Services & Consulting", "Fintech", "B2B SaaS"
"stage"              — Funding stage if mentioned: Seed / Series A / Series B / bootstrapped / public
"about_role"         — 2–5 sentence paragraph describing the role (combine overview + context sections)
"first_90_days"      — What this person will own and deliver (from responsibilities, brief 1–2 sentences)
"dealbreaker"        — Hard requirements / must-haves (1–2 sentences)
"culture_signal"     — Team culture, values, working style (1–2 sentences)
"why_join"           — What makes this company or role exciting (1–2 sentences)
"company_description" — 2–4 sentence description of the company from the "About" section
"company_size"       — Employee count range, e.g. "201–500" or "1,000+"
"company_website"    — Website URL if present (exact URL, no inference)
"company_linkedin"   — LinkedIn company page URL if present (exact URL)
"equity"             — ESOP / equity offer if mentioned
"hiring_urgency"     — Timeline or urgency signal if mentioned

## LIST KEYS (return as JSON arrays of strings, NOT comma-separated strings):

"skills_tags"             — All skills, technologies, and tools as short individual tags
                             e.g. ["Python", "SQL", "Machine Learning", "Demand Forecasting"]
                             Include both required and preferred skills; deduplicate; max 20 items
"responsibilities"        — Bullet-point list of key responsibilities (each item is one sentence)
                             Extract from "Key Responsibilities", "What you'll do", etc.
"required_skills"         — Bullet-point list of required skills/experience (each item is one sentence)
                             Extract from "Required Skills", "Must have", "Qualifications" sections
"preferred_qualifications" — Bullet-point list of nice-to-have qualifications (each item one sentence)
                             Extract from "Preferred", "Nice to have", "Bonus" sections

## IMPORTANT:
- "skills_tags" must be an array of short tag strings (2–4 words max each)
- "responsibilities", "required_skills", "preferred_qualifications" must be arrays of full sentences
- All other keys must be plain strings
- Omit a key entirely if the section does not exist in the JD"""


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
    text = await extract_text_from_pdf(data)
    if not text:
        text = await extract_text_from_docx(data)
    return text


# Keys that should remain as lists (not flattened to strings)
_LIST_KEYS = {"skills_tags", "responsibilities", "required_skills", "preferred_qualifications"}


async def extract_jd_signals(text: str, settings: Settings) -> dict[str, Any]:
    """
    Call the LLM to extract structured hiring signals from raw JD text.

    Returns a mixed dict:
    - String fields for standard session store keys
    - List fields (for _LIST_KEYS) stored as JSON strings so the session store
      can persist them; the upload endpoint parses them back to lists for the preview.
    """
    if not text or len(text) < 30:
        log.warning("JD text too short to parse (%d chars)", len(text))
        return {}

    truncated = text[:12000]  # increased for richer JDs

    adapter = get_llm_adapter(settings)
    try:
        result = await adapter.complete(
            model=settings.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_EXTRACT_SYSTEM),
                ChatMessage(role="user",   content=f"JOB DESCRIPTION:\n\n{truncated}"),
            ],
            tools=None,
            max_tokens=2048,
            temperature=0.0,
        )
    except Exception:
        log.exception("JD extraction LLM call failed")
        return {}

    raw = (result.content or "").strip()
    if not raw:
        log.warning("LLM returned empty response for JD extraction")
        return {}

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

    clean: dict[str, Any] = {}
    for k, v in signals.items():
        if v is None:
            continue
        key = str(k)
        if key in _LIST_KEYS:
            # Normalize: ensure it's a list of strings
            if isinstance(v, list):
                items = [str(i).strip() for i in v if str(i).strip()]
            else:
                # Model returned a string despite instructions — split on newlines/bullets
                items = [
                    line.lstrip("•-* ").strip()
                    for line in str(v).split("\n")
                    if line.strip().lstrip("•-* ")
                ]
            if items:
                # Store as JSON string so the session store (which expects str values) is happy
                clean[key] = json.dumps(items, ensure_ascii=False)
        else:
            clean[key] = str(v) if not isinstance(v, str) else v

    log.info("JD extraction: found %d signals — %s", len(clean), sorted(clean.keys()))
    return clean


def parse_list_signal(value: Any) -> list[str]:
    """
    Safely parse a signal value that should be a list.
    Handles JSON strings, plain lists, and falls back gracefully.
    """
    if isinstance(value, list):
        return [str(i) for i in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(i) for i in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
        # Plain comma or newline separated
        if "\n" in value:
            return [line.lstrip("•-* ").strip() for line in value.split("\n") if line.strip()]
        return [s.strip() for s in value.split(",") if s.strip()]
    return []
