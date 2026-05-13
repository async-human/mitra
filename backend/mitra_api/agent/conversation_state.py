"""
mitra_api/agent/conversation_state.py

Computed-per-turn view that integrates signals, reflection, interpretation,
and contradictions into a single structured object the agent reads.

NOT a new persistent store — derived from existing stores every turn.
Two persistent additions: `_asked_log` (per-question topic log) and
`_probed_dimensions` (already used by contradictions.py).

Public API
----------
TopicId                       — enum of conversational topics
compute_state(...)            — main entry point, returns ConversationState
tag_question(text)            — classify an agent question into a TopicId
ConversationState.to_prompt_block() — single string injected into the prompt
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

log = logging.getLogger(__name__)


# ── TopicId ────────────────────────────────────────────────────────────────────

class TopicId(str, Enum):
    """
    Hard-coded set of conversational topics. The string value is what we store
    in `_asked_log` and what shows up in the prompt block.

    1:1 with the signal keys used by score_conversation_quality + a handful of
    probe-only topics that have no associated signal.
    """
    MOTIVATION       = "motivation"
    CURRENT_ROLE     = "current_role"
    STACK            = "primary_stack"
    YEARS_EXP        = "years_experience"
    SALARY           = "salary_floor_lpa"
    LOCATION         = "location_preference"
    STAGE_PREF       = "startup_stage_pref"
    NOTICE           = "notice_period_days"
    DEALBREAKERS     = "dealbreakers"
    WHAT_THEY_WANT   = "what_they_want"
    INDUSTRIES       = "industries"
    PROJECTS         = "projects_built"
    COMPETING_OFFERS = "competing_offers"
    # Probing topics — no associated signal
    PROBE_AMBITION    = "probe:ambition"
    PROBE_CONSTRAINTS = "probe:hidden_constraints"
    TENSION_PROBE     = "probe:tension"

    @classmethod
    def from_value(cls, value: str) -> "TopicId | None":
        for t in cls:
            if t.value == value:
                return t
        return None


# ── Topic patterns ─────────────────────────────────────────────────────────────
# Regex catalog — used by tag_question() to classify an agent question.
# Conservative: a question that matches nothing returns None (graceful degrade).

_TOPIC_PATTERNS: dict[TopicId, list[re.Pattern[str]]] = {
    TopicId.MOTIVATION: [
        # "why are you thinking about a move" / "what's making you consider new opportunities"
        re.compile(r"\b(why|what)\b.{0,40}\b(thinking|considering)\b.{0,30}\b(move|change|switch|leaving|new\s+(role|job|opportunit))\b", re.I),
        # "what's driving / motivating / pushing"
        re.compile(r"\bwhat'?s\b.{0,30}\b(driving|motivating|pushing|behind)\b", re.I),
        # "what's making you / got you thinking"
        re.compile(r"\bwhat'?s\b.{0,15}\b(making you|got you)\b.{0,15}\b(think|consider)\b", re.I),
        re.compile(r"\bwhat brings (you|brought you)\b", re.I),
        re.compile(r"\b(reason|story) (for|behind)\b.{0,20}\b(move|change|switch|leaving)\b", re.I),
        # "exploring new opportunities" — common rephrase of "why are you moving"
        re.compile(r"\bexplor(e|ing).{0,15}\bnew\s+opportunities\b", re.I),
    ],
    TopicId.CURRENT_ROLE: [
        re.compile(r"\bwhat (do you|are you) (do|doing)\b.{0,15}\b(now|currently|today)\b", re.I),
        re.compile(r"\b(current|present) (role|job|position|title)\b", re.I),
        re.compile(r"\bwhere (do you|are you) work(ing)?\b", re.I),
        re.compile(r"\bwhat'?s your (role|title|job)\b", re.I),
    ],
    TopicId.STACK: [
        re.compile(r"\b(tech|technical) (stack|skills?)\b", re.I),
        re.compile(r"\bwhat (technologies|tools|languages|frameworks)\b", re.I),
        re.compile(r"\bwhich (languages|frameworks|stack)\b", re.I),
        re.compile(r"\bwhat (do|have) you (work(ed)?|build) with\b", re.I),
    ],
    TopicId.YEARS_EXP: [
        re.compile(r"\bhow (many years|long).{0,15}\bexperience\b", re.I),
        re.compile(r"\byears? of (experience|exp)\b", re.I),
        re.compile(r"\bhow long.{0,15}\b(been|in the industry|coding)\b", re.I),
    ],
    TopicId.SALARY: [
        re.compile(r"\b(salary|comp(ensation)?|ctc|package)\b", re.I),
        re.compile(r"\b(how much|what).{0,20}\b(make|earn|paid|expecting|looking for)\b", re.I),
        re.compile(r"\bsalary expectation\b", re.I),
        re.compile(r"\b₹|\blpa\b|\blakhs?\b|\bcrore\b", re.I),
    ],
    TopicId.LOCATION: [
        re.compile(r"\b(where|location|city).{0,30}\b(based|live|work|prefer|relocate)\b", re.I),
        re.compile(r"\b(remote|hybrid|onsite|on-site|in-office)\b.{0,20}\b(preference|work|open)\b", re.I),
        re.compile(r"\bopen to (relocating|relocation|moving)\b", re.I),
        re.compile(r"\bwhich city\b", re.I),
    ],
    TopicId.STAGE_PREF: [
        re.compile(r"\b(stage|seed|series [a-d]|early|late)\b.{0,30}\b(prefer|stage|company|startup)\b", re.I),
        re.compile(r"\bwhat (size|stage|kind) of (company|startup|team)\b", re.I),
        re.compile(r"\b(early|late)-?stage\b", re.I),
        re.compile(r"\bbig (company|tech)\b.{0,15}\b(or|vs)\b.{0,15}\bstartup\b", re.I),
    ],
    TopicId.NOTICE: [
        re.compile(r"\bnotice period\b", re.I),
        re.compile(r"\bhow (soon|quickly|fast).{0,20}\b(start|join|move)\b", re.I),
        re.compile(r"\bwhen (could|can) you (start|join)\b", re.I),
        re.compile(r"\bavailability\b.{0,20}\bstart\b", re.I),
    ],
    TopicId.DEALBREAKERS: [
        re.compile(r"\bdeal[\s-]?breakers?\b", re.I),
        re.compile(r"\bwhat (would|will) you (never|not) accept\b", re.I),
        re.compile(r"\banything (you'?d?|that)\b.{0,15}\b(rule out|avoid|won'?t consider)\b", re.I),
        re.compile(r"\bred flags?\b", re.I),
    ],
    TopicId.WHAT_THEY_WANT: [
        re.compile(r"\bwhat (kind of|type of|sort of) (role|job|position)\b", re.I),
        re.compile(r"\bwhat (roles|positions|titles) are you (looking|targeting|aiming|exploring)\b", re.I),
        re.compile(r"\bwhich role\b", re.I),
        re.compile(r"\btarget(ing)? (role|position|job)\b", re.I),
    ],
    TopicId.INDUSTRIES: [
        re.compile(r"\b(which|what) (industry|industries|sector|sectors|domain|domains)\b", re.I),
        re.compile(r"\binterested in.{0,30}\b(industry|sector|space|domain)\b", re.I),
        re.compile(r"\b(fintech|healthtech|edtech|saas|crypto|web3|ai/ml|consumer)\b", re.I),
    ],
    TopicId.PROJECTS: [
        re.compile(r"\b(project|projects|something you('ve| have)? built)\b", re.I),
        re.compile(r"\b(tell me about|describe).{0,30}\b(project|something you (built|shipped))\b", re.I),
        re.compile(r"\bwhat (have you|did you) (built|ship(ped)?|create|work on)\b", re.I),
        re.compile(r"\bproudest (work|project|build)\b", re.I),
    ],
    TopicId.COMPETING_OFFERS: [
        re.compile(r"\b(competing|other)\s+(offers?|interviews?|processes)\b", re.I),
        re.compile(r"\b(in process|interview(ing)?) with.{0,15}\b(other|another)\b", re.I),
        re.compile(r"\b(any|other) offers? (on the table|in hand)\b", re.I),
    ],
    TopicId.PROBE_AMBITION: [
        re.compile(r"\b(where|how) do you see yourself\b", re.I),
        re.compile(r"\bin (2|3|5) years\b", re.I),
        re.compile(r"\b(ambition|aspiration)s?\b", re.I),
        re.compile(r"\b(next chapter|next stage|next move)\b", re.I),
    ],
    TopicId.PROBE_CONSTRAINTS: [
        re.compile(r"\bvisa\b", re.I),
        re.compile(r"\bfamily (commitment|situation|reason)\b", re.I),
        re.compile(r"\b(loan|emi|mortgage|dependents?)\b", re.I),
        re.compile(r"\b(health|medical) (condition|reason)\b", re.I),
    ],
}


# Imperative elicitations the agent uses ("tell me about", "walk me through", etc.)
# also count as questions for topic-tagging purposes.
_ELICITATION_PREFIX = re.compile(
    r"\b(tell me|walk me through|describe|share|talk to me|help me understand)\b",
    re.I,
)


def tag_question(text: str) -> TopicId | None:
    """Classify an agent question into a topic. Returns None if no pattern matches."""
    if not text:
        return None
    for topic, patterns in _TOPIC_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            return topic
    return None


def _is_elicitation(sentence: str) -> bool:
    s = sentence.rstrip()
    return s.endswith("?") or bool(_ELICITATION_PREFIX.search(s))


def _extract_last_question(assistant_text: str) -> str | None:
    """
    Pull the last sentence that elicits information from an assistant message.
    Recognises both "?"-ending questions and imperative elicitations
    ("Tell me about X", "Walk me through Y").
    """
    if not assistant_text:
        return None
    parts = re.split(r"(?<=[.!?])\s+", assistant_text.strip())
    elicitations = [p for p in parts if _is_elicitation(p)]
    return elicitations[-1] if elicitations else None


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class ConfirmedSignal:
    key:           str
    value:         Any
    confidence:    float
    mention_count: int = 1


@dataclass
class OpenSlot:
    key:             str
    topic:           TopicId
    weight:          int
    last_asked_turn: int | None = None
    times_asked:     int = 0


@dataclass
class AskedQuestion:
    topic:    str          # TopicId.value (stored as string for JSON safety)
    turn_idx: int
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "turn_idx": self.turn_idx, "raw_text": self.raw_text[:300]}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AskedQuestion":
        return cls(
            topic=str(d.get("topic", "")),
            turn_idx=int(d.get("turn_idx", 0)),
            raw_text=str(d.get("raw_text", "")),
        )


@dataclass
class ProbedTension:
    dimension:   str
    severity:    Literal["soft", "hard"]
    confidence:  float
    is_probed:   bool        # True once we've already raised it


# Workflow stage — broad operational phase.
WorkflowStage = Literal[
    "intake",          # collecting initial signals
    "deepening",       # have basics, exploring nuance
    "ready_to_search", # have enough — should be calling search_jobs
    "shortlisting",    # search results presented, awaiting selection
    "intro_pending",   # candidate selected, intro being prepared
    "negotiating",     # offer in motion
]


# Next-action kinds the agent can take this turn.
NextActionKind = Literal[
    "collect_signal",   # ask a question on a specific topic
    "deepen_signal",    # signal exists but is thin — go deeper
    "probe_tension",    # surface a candidate-internal tension
    "search_jobs",      # call the search_jobs tool
    "present_matches",  # show shortlist cards
    "request_intro",    # call request_intro tool
    "free_response",    # no specific action — just respond naturally
]


@dataclass
class NextAction:
    kind:      NextActionKind
    topic:     str | None = None        # TopicId.value when relevant
    tension:   str | None = None        # contradiction dimension when relevant
    rationale: str = ""

    def to_block_line(self) -> str:
        bits = [f"kind={self.kind}"]
        if self.topic:
            bits.append(f"topic={self.topic}")
        if self.tension:
            bits.append(f"tension={self.tension}")
        return " · ".join(bits)


@dataclass
class ConversationState:
    turn_idx:         int
    stage:            WorkflowStage
    readiness_pct:    int
    confirmed:        list[ConfirmedSignal]
    open_slots:       list[OpenSlot]
    asked:            list[AskedQuestion]
    probed_tensions:  list[ProbedTension]
    next_action:      NextAction
    emotional_tone:   str | None = None
    behavioral_shift: str | None = None
    remember:         str | None = None
    # Hints carried from rule-based extraction (e.g. framing)
    framing_hint:     str | None = None

    def to_prompt_block(self) -> str:
        """Single [CONVERSATION STATE] block injected into the prompt."""
        lines = ["[CONVERSATION STATE — single source of truth this turn]"]
        lines.append(
            f"Stage: {self.stage} · Readiness: {self.readiness_pct}% · Turn: {self.turn_idx}"
        )

        if self.confirmed:
            confirmed_str = " · ".join(
                f"{c.key}={_short(c.value)}" for c in self.confirmed[:12]
            )
            lines.append(f"Confirmed: {confirmed_str}")

        if self.open_slots:
            slot_strs = []
            for s in self.open_slots[:5]:
                tag = f"{s.key}"
                if s.times_asked:
                    tag += f"(asked×{s.times_asked})"
                slot_strs.append(tag)
            lines.append(f"Open slots (by priority): {', '.join(slot_strs)}")

        if self.asked:
            asked_topics = ", ".join(sorted({a.topic for a in self.asked}))
            lines.append(f"Already asked this conversation: {asked_topics}")

        unresolved_tensions = [t for t in self.probed_tensions if not t.is_probed]
        if unresolved_tensions:
            tlist = ", ".join(
                f"{t.dimension}({t.severity}, {t.confidence:.2f})"
                for t in unresolved_tensions[:3]
            )
            lines.append(f"Active tensions: {tlist}")

        if self.emotional_tone or self.behavioral_shift:
            tone_bits = []
            if self.emotional_tone:
                tone_bits.append(f"tone={self.emotional_tone}")
            if self.behavioral_shift:
                tone_bits.append(f"shift={self.behavioral_shift}")
            lines.append(f"Behavior: {' · '.join(tone_bits)}")

        if self.remember:
            lines.append(f"Remember: {self.remember}")

        if self.framing_hint:
            lines.append(f"Framing for any role presentation: {self.framing_hint}")

        lines.append("")
        lines.append(f"[NEXT ACTION] {self.next_action.to_block_line()}")
        if self.next_action.rationale:
            lines.append(f"Rationale: {self.next_action.rationale}")

        return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────────────────

_INTAKE_WEIGHTS = {
    "motivation":           25,
    "primary_stack":        20,
    "salary_floor_lpa":     15,
    "location_preference":  10,
    "startup_stage_pref":   10,
    "current_role":          8,
    "notice_period_days":    7,
    "dealbreakers":          5,
}

# Map signal_key → TopicId.value so we can ask the right kind of question.
_KEY_TO_TOPIC = {
    "motivation":          TopicId.MOTIVATION.value,
    "primary_stack":       TopicId.STACK.value,
    "salary_floor_lpa":    TopicId.SALARY.value,
    "salary_target_lpa":   TopicId.SALARY.value,
    "location_preference": TopicId.LOCATION.value,
    "startup_stage_pref":  TopicId.STAGE_PREF.value,
    "current_role":        TopicId.CURRENT_ROLE.value,
    "notice_period_days":  TopicId.NOTICE.value,
    "dealbreakers":        TopicId.DEALBREAKERS.value,
    "what_they_want":      TopicId.WHAT_THEY_WANT.value,
    "industries":          TopicId.INDUSTRIES.value,
}


def _short(value: Any, max_len: int = 40) -> str:
    """Compact a value for the prompt block."""
    if isinstance(value, list):
        s = ", ".join(str(v) for v in value[:4])
    elif isinstance(value, dict):
        s = str({k: value[k] for k in list(value.keys())[:3]})
    else:
        s = str(value)
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _build_confirmed(
    known_signals: dict[str, Any],
    last_interpretation: dict[str, Any] | None,
) -> list[ConfirmedSignal]:
    """
    Build the confirmed list. Confidence is enriched from the last interpretation
    output when available (interpreter outputs per-signal confidence).
    """
    # Confidence map from interpretation (if any)
    conf_map: dict[str, float] = {}
    if last_interpretation:
        for sig in last_interpretation.get("signals", []):
            key = sig.get("signal_key", "")
            try:
                c = float(sig.get("confidence", 0.0))
            except (TypeError, ValueError):
                c = 0.0
            if key:
                conf_map[key] = max(conf_map.get(key, 0.0), c)

    out: list[ConfirmedSignal] = []
    # We surface the most "important" confirmed signals first — intake weights
    # decide order; everything else falls through.
    priority_keys = list(_INTAKE_WEIGHTS.keys()) + [
        "candidate_name", "what_they_want", "years_experience", "current_company",
        "industries", "secondary_stack",
    ]
    seen: set[str] = set()
    for k in priority_keys:
        if k in known_signals and known_signals[k] not in (None, "", []):
            out.append(ConfirmedSignal(
                key=k, value=known_signals[k],
                confidence=conf_map.get(k, 0.85),  # default high — present means confirmed
            ))
            seen.add(k)
    # Catch any other top-level signals not in the priority list
    for k, v in known_signals.items():
        if k in seen or k.startswith("_") or v in (None, "", []):
            continue
        out.append(ConfirmedSignal(
            key=k, value=v, confidence=conf_map.get(k, 0.75),
        ))
    return out


def _build_open_slots(
    known_signals: dict[str, Any],
    asked: list[AskedQuestion],
) -> list[OpenSlot]:
    """Slots from the intake weights that don't have a value yet, sorted by weight desc."""
    asked_by_topic: dict[str, list[AskedQuestion]] = {}
    for a in asked:
        asked_by_topic.setdefault(a.topic, []).append(a)

    out: list[OpenSlot] = []
    for key, weight in _INTAKE_WEIGHTS.items():
        if known_signals.get(key) in (None, "", []):
            topic_value = _KEY_TO_TOPIC.get(key, key)
            topic = TopicId.from_value(topic_value)
            if topic is None:
                continue
            history = asked_by_topic.get(topic_value, [])
            out.append(OpenSlot(
                key=key,
                topic=topic,
                weight=weight,
                last_asked_turn=history[-1].turn_idx if history else None,
                times_asked=len(history),
            ))
    out.sort(key=lambda s: (-s.weight, s.times_asked))
    return out


def _build_probed_tensions(
    contradictions: list[dict[str, Any]] | None,
    probed_dimensions: list[str] | None,
) -> list[ProbedTension]:
    probed = set(probed_dimensions or [])
    out: list[ProbedTension] = []
    for c in (contradictions or []):
        if not isinstance(c, dict):
            continue
        sev = c.get("severity", "soft")
        if sev not in ("soft", "hard"):
            sev = "soft"
        out.append(ProbedTension(
            dimension=str(c.get("dimension", "")),
            severity=sev,  # type: ignore[arg-type]
            confidence=float(c.get("confidence", 0.0)),
            is_probed=(c.get("dimension") in probed),
        ))
    # Hardest, highest-confidence, unprobed first
    out.sort(key=lambda t: (
        0 if t.is_probed else 1,
        1 if t.severity == "hard" else 0,
        t.confidence,
    ), reverse=True)
    return out


def _infer_stage(
    confirmed: list[ConfirmedSignal],
    last_reflection: dict[str, Any] | None,
    readiness_pct: int,
    transcript_len: int,
) -> WorkflowStage:
    """
    Heuristic stage inference. Refection.phase wins when present; otherwise
    derive from readiness % and transcript length.
    """
    if last_reflection:
        phase = (last_reflection.get("phase") or "").strip()
        if phase == "interviewing":
            return "intro_pending"
        if phase == "negotiating":
            return "negotiating"

    if readiness_pct >= 70:
        return "ready_to_search"
    if readiness_pct >= 40 or transcript_len > 10:
        return "deepening"
    return "intake"


def _decide_next_action(
    *,
    stage: WorkflowStage,
    readiness_pct: int,
    open_slots: list[OpenSlot],
    probed_tensions: list[ProbedTension],
    is_intro_pending: bool = False,
) -> NextAction:
    """
    The single integration point. Decides what the agent should do this turn.
    Hard tensions trump intake; intake trumps soft tensions; readiness gates search.
    """
    # 1. Hard, high-confidence, unprobed tension > everything else
    hard_unprobed = [
        t for t in probed_tensions
        if not t.is_probed and t.severity == "hard" and t.confidence >= 0.75
    ]
    if hard_unprobed:
        t = hard_unprobed[0]
        return NextAction(
            kind="probe_tension", tension=t.dimension,
            rationale=f"Hard tension on '{t.dimension}' — probe before continuing intake.",
        )

    # 2. Below readiness threshold → collect the highest-weight missing slot
    if readiness_pct < 60 and open_slots:
        # Skip slots we've already asked twice with no answer
        fresh = next((s for s in open_slots if s.times_asked < 2), None)
        target = fresh or open_slots[0]
        if target.times_asked == 0:
            rationale = f"Most valuable missing signal: {target.key}. Ask one natural question on this topic."
        else:
            rationale = (
                f"Re-approach {target.key} from a fresh angle (asked {target.times_asked}× before, "
                "no usable answer). If you re-approach, do not re-use prior wording."
            )
        return NextAction(
            kind="collect_signal", topic=target.topic.value, rationale=rationale,
        )

    # 3. Soft tension worth surfacing now that intake is sufficient
    soft_unprobed = [
        t for t in probed_tensions
        if not t.is_probed and t.confidence >= 0.6
    ]
    if soft_unprobed and readiness_pct >= 60:
        t = soft_unprobed[0]
        return NextAction(
            kind="probe_tension", tension=t.dimension,
            rationale=f"Soft tension on '{t.dimension}' — gentle probe; intake is sufficient.",
        )

    # 4. Ready to search
    if stage == "ready_to_search" and not is_intro_pending:
        return NextAction(
            kind="search_jobs",
            rationale="Intake complete (readiness ≥ 70%). Call search_jobs now — no more questions.",
        )

    # 5. Deepen one of the present signals if we have basics but nothing to do
    if readiness_pct >= 40 and not open_slots:
        return NextAction(
            kind="deepen_signal", topic=TopicId.PROBE_AMBITION.value,
            rationale="Have basics — deepen ambition or projects before searching.",
        )

    # 6. Default — free response
    return NextAction(
        kind="free_response",
        rationale="No specific action — react to what they said and follow their lead.",
    )


# ── Public entry ──────────────────────────────────────────────────────────────

def compute_state(
    *,
    turn_idx:            int,
    known_signals:       dict[str, Any],
    transcript_len:      int,
    last_reflection:     dict[str, Any] | None,
    last_interpretation: dict[str, Any] | None,
    contradictions:      list[dict[str, Any]] | None,
    probed_dimensions:   list[str] | None,
    asked_log:           list[AskedQuestion],
    readiness_pct:       int,
    framing_hint:        str | None = None,
    is_intro_pending:    bool = False,
) -> ConversationState:
    """
    Build the per-turn ConversationState view from existing data sources.
    Pure function; no I/O.
    """
    confirmed = _build_confirmed(known_signals, last_interpretation)
    open_slots = _build_open_slots(known_signals, asked_log)
    tensions = _build_probed_tensions(contradictions, probed_dimensions)
    stage = _infer_stage(confirmed, last_reflection, readiness_pct, transcript_len)
    next_action = _decide_next_action(
        stage=stage,
        readiness_pct=readiness_pct,
        open_slots=open_slots,
        probed_tensions=tensions,
        is_intro_pending=is_intro_pending,
    )

    refl = last_reflection or {}
    return ConversationState(
        turn_idx=turn_idx,
        stage=stage,
        readiness_pct=readiness_pct,
        confirmed=confirmed,
        open_slots=open_slots,
        asked=asked_log,
        probed_tensions=tensions,
        next_action=next_action,
        emotional_tone=refl.get("emotional_tone") if isinstance(refl, dict) else None,
        behavioral_shift=refl.get("behavioral_shift") if isinstance(refl, dict) else None,
        remember=refl.get("remember") if isinstance(refl, dict) else None,
        framing_hint=framing_hint,
    )


def load_asked_log(raw: Any) -> list[AskedQuestion]:
    """Coerce the persisted `_asked_log` blob into a typed list."""
    if not isinstance(raw, list):
        return []
    out: list[AskedQuestion] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            out.append(AskedQuestion.from_dict(entry))
        except Exception:
            continue
    return out


def append_asked(
    asked_log: list[AskedQuestion],
    *,
    assistant_text: str,
    turn_idx: int,
    max_size: int = 50,
) -> tuple[list[AskedQuestion], str | None]:
    """
    Tag the assistant's last question and append to the log.
    Returns (new_log, topic_tagged_or_None).
    De-dupes consecutive entries on the same topic.
    """
    last_q = _extract_last_question(assistant_text)
    if not last_q:
        return asked_log, None
    topic = tag_question(last_q)
    if topic is None:
        return asked_log, None

    new_entry = AskedQuestion(topic=topic.value, turn_idx=turn_idx, raw_text=last_q)
    # Avoid storing duplicate consecutive entries on the same topic
    if asked_log and asked_log[-1].topic == new_entry.topic and asked_log[-1].turn_idx == turn_idx:
        return asked_log, topic.value

    new_log = list(asked_log) + [new_entry]
    if len(new_log) > max_size:
        new_log = new_log[-max_size:]
    return new_log, topic.value
