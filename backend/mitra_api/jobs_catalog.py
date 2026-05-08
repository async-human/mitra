"""Load curated Mitra demo jobs from JSON (replaces inlined Python catalog)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_JOBS_JSON = Path(__file__).resolve().parent / "data" / "jobs.json"


def load_job_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _JOBS_JSON
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("jobs catalog must be a JSON array")

    normalized: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f"job entry {i} must be an object")

        signals = row.get("signals", [])
        if isinstance(signals, (list, tuple)):
            row = {**row, "signals": set(str(s) for s in signals)}
        elif signals is None:
            row = {**row, "signals": set()}
        elif not isinstance(signals, set):
            row = {**row, "signals": set()}
        normalized.append(row)
    return normalized
