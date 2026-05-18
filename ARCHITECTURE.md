# Mitra — System Architecture & Feature Map

> Complete reference for how Mitra works end-to-end: every feature, every workflow, every design decision.

---

## Table of Contents

1. [What Mitra Is](#1-what-mitra-is)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Database Schema](#3-database-schema)
4. [Candidate Workflow](#4-candidate-workflow)
5. [The AI Agent](#5-the-ai-agent)
6. [Agent Tools (all 6)](#6-agent-tools)
7. [Founder Workflow](#7-founder-workflow)
8. [Intro Lifecycle](#8-intro-lifecycle)
9. [Proactive Job Alerts](#9-proactive-job-alerts)
10. [Admin System](#10-admin-system)
11. [Frontend Pages](#11-frontend-pages)
12. [Infrastructure & Config](#12-infrastructure--config)

---

## 1. What Mitra Is

Mitra is a two-sided AI talent marketplace for India's startup ecosystem.

**Candidates** interact exclusively over WhatsApp. Mitra acts as their personal AI talent agent — understanding their background, searching for matching roles, and making warm introductions to founders on their behalf.

**Founders** post jobs via a web chat and review candidate introductions via a no-login token-gated portal.

**The core metric** is the intro → hire funnel. Every introduction Mitra makes is tracked from `sent` all the way to `hired`.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     WhatsApp (Candidate)                 │
│  Meta Cloud API  ◄──────────────────────►  Twilio       │
└─────────────┬───────────────────────────────┬───────────┘
              │ webhook                        │ webhook
              ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  /webhook/whatsapp   /webhook/twilio/whatsapp            │
│         │                     │                          │
│         └──────── inbound.py ─┘                          │
│                       │                                  │
│              orchestrator.py (ReAct agent loop)          │
│                       │                                  │
│    ┌──────────────────┴──────────────────┐              │
│    │           6 Agent Tools              │              │
│    │  search_jobs  remember_signals        │              │
│    │  get_salary_benchmark request_intro  │              │
│    │  check_intro_status  parse_resume    │              │
│    └──────────────────┬──────────────────┘              │
│                       │                                  │
│    ┌──────────────────┴──────────────────┐              │
│    │     PostgreSQL + pgvector + Redis    │              │
│    └─────────────────────────────────────┘              │
│                                                          │
│  /founder/*   /admin/*   /candidate/*                    │
└─────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│               Next.js Web App (Founder + Admin)          │
│                                                          │
│  /founder/setup   → founder onboarding chat              │
│  /founder/portal  → candidate pipeline (token-gated)     │
│  /admin           → ops metrics dashboard (key-gated)    │
│  /chat            → web-based candidate interface        │
└─────────────────────────────────────────────────────────┘
```

**LLM Providers:** Anthropic (Claude) or OpenAI — switchable via `MITRA_LLM_PROVIDER`.
**Embedding Providers:** Voyage AI (recommended) or OpenAI — for semantic job search.
**Email:** Resend API.
**Session store:** Redis (production) or in-memory (development).

---

## 3. Database Schema

### `candidates`
One row per unique WhatsApp sender. `phone` is the E.164 number (e.g. `+919405109606`). Web candidates use `web:{email}` as the phone value.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `phone` | varchar(32) unique | WhatsApp sender ID or `web:{email}` |
| `name` | varchar(200) | |
| `current_role` | varchar(200) | |
| `current_company` | varchar(200) | |
| `years_exp` | int | |
| `resume_text` | text | Extracted from PDF if uploaded |
| `is_active` | bool | |
| `created_at` / `updated_at` | timestamptz | |

### `candidate_signals`
Key-value store of everything the agent learns about a candidate. Uses JSONB so values can be strings, ints, lists, or booleans.

| Key (examples) | Value type | Meaning |
|---|---|---|
| `primary_stack` | list | `["Python", "FastAPI", "PostgreSQL"]` |
| `motivation` | str | Why they want to move |
| `salary_floor_lpa` | int | Minimum acceptable salary |
| `salary_target_lpa` | int | Desired salary |
| `location_preference` | list | `["Remote", "Bengaluru"]` |
| `startup_stage_pref` | list | `["Series A", "Series B"]` |
| `dealbreakers` | list | `["crypto", "bond periods"]` |
| `notice_period_days` | int | |
| `actively_looking` | bool | |
| `years_experience` | int | |

Unique constraint on `(candidate_id, key)` — updates overwrite.

### `jobs`
The canonical job catalogue, managed via the admin API.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `external_id` | varchar unique | Your own reference (e.g. `mtr-001`) |
| `status` | varchar | `active`, `paused`, `filled`, `expired` |
| `title` | varchar | |
| `company` | varchar | |
| `stage` | varchar | `seed`, `Series A`, `Series B`, etc. |
| `sector` | varchar | `Fintech`, `B2B SaaS`, etc. |
| `location` | varchar | |
| `remote_policy` | varchar | `remote`, `hybrid`, `onsite` |
| `employment` | varchar | `full_time`, `contract` |
| `salary_min_lpa` | int | |
| `salary_max_lpa` | int | |
| `stack` | JSONB | `["Python", "FastAPI"]` |
| `signals` | JSONB | Custom tags like `["backend-heavy", "fintech"]` |
| `summary` | text | Why-join blurb shown to candidates |
| `full_jd` | text | Full job description |
| `founder_name` | varchar | |
| `founder_email` | varchar | Intro delivery channel |
| `founder_wa` | varchar | Intro delivery channel (preferred) |
| `founder_access_token` | varchar(64) | Persistent no-login portal token |

### `job_embeddings`
Separate table to keep `jobs` lean. Stores the pgvector embedding for semantic search.

| Column | Notes |
|---|---|
| `job_id` | FK to jobs (unique) |
| `model` | Embedding model used |
| `dimensions` | 1536 (OpenAI) or 1024 (Voyage) |
| `embedding` | `vector(N)` — native pgvector column, added via raw DDL |

Index: IVFFlat cosine similarity index on `embedding`.

### `intros`
Every introduction Mitra makes. The core business table.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `candidate_id` | FK candidates | |
| `job_id` | FK jobs | |
| `status` | varchar | See IntroStatus enum below |
| `intro_note` | text | The actual intro message sent to founder |
| `response_token` | varchar(64) unique | One-click founder reply token |
| `requested_at` | timestamptz | When candidate asked for intro |
| `sent_at` | timestamptz | When intro was delivered to founder |
| `interview_at` | timestamptz | Timestamp when moved to `interview` |
| `offer_at` | timestamptz | Timestamp when moved to `offer` |
| `hired_at` | timestamptz | Timestamp when moved to `hired` |
| `updated_at` | timestamptz | |

**IntroStatus enum:**

| Value | Meaning |
|---|---|
| `sent` | Intro delivered to founder, awaiting response |
| `acknowledged` | Founder clicked "Interested" |
| `interview` | Interview booked |
| `offer` | Offer extended |
| `hired` | Candidate joined |
| `declined` | Founder passed |
| `ghosted` | No reply after 7 days (auto-set on portal load) |

### `salary_benchmarks`
India startup salary survey data. Fallback when job listings don't have salary info.

| Column | Notes |
|---|---|
| `role_category` | e.g. `backend engineer`, `ml engineer` |
| `stage` | e.g. `Series A` |
| `seniority` | e.g. `senior`, `lead` |
| `p25_lpa` / `median_lpa` / `p75_lpa` | Percentile benchmarks in LPA |
| `source` | e.g. `Levels.fyi India 2025-Q1` |

---

## 4. Candidate Workflow

### Entry Points
1. **WhatsApp (Meta Cloud API)** — webhook at `POST /webhook/whatsapp`. Requires `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`.
2. **WhatsApp (Twilio)** — webhook at `POST /webhook/twilio/whatsapp`. Requires Twilio credentials. This is the primary channel used in production/sandbox.
3. **Web chat** — `/chat` page in the Next.js app. Same agent, different interface.

### Message Processing Pipeline

```
Incoming WhatsApp message
        │
        ▼
Signature verification (HMAC-SHA256 for Meta, Twilio signature for Twilio)
        │
        ▼
Extract (from_id, body_text, media_url, media_type) from webhook payload
        │
        ▼
run_agent_reply() — kicked off as a BackgroundTask (webhook returns 200 immediately)
        │
        ▼
run_agent_turn() in orchestrator.py
        │
        ├─ Load candidate signals from Redis (fast path)
        │   └─ Fallback to Postgres if Redis is empty (e.g. after restart)
        │
        ├─ Load conversation transcript from Redis
        │
        ├─ If PDF attached: auto-parse resume BEFORE LLM turn
        │   └─ Signals extracted and saved to Redis + Postgres immediately
        │
        ├─ Inject context system messages:
        │   ├─ Known profile signals
        │   ├─ Returning candidate greeting (if transcript expired but signals exist)
        │   ├─ Fresh start instructions (if candidate said "start over")
        │   └─ Weak-intro nudge (if past intros were sent with thin profile data)
        │
        ├─ ReAct agent loop (max 8 rounds by default):
        │   ├─ Call LLM with tools + full message history
        │   ├─ If tool calls → execute tools → append results → loop
        │   └─ If no tool calls → final text ready → exit loop
        │
        ├─ Save new messages to Redis transcript
        │
        └─ Send response via WhatsApp
            ├─ If job results present AND MITRA_WHATSAPP_NATIVE_LIST=true:
            │   ├─ Try Meta interactive list message
            │   └─ Try Twilio interactive list message
            └─ Fallback: split long text into ≤4096-char plain messages
```

### Session Store

- **Redis (production):** `mitra:session:{phone}:msgs` stores transcript. `mitra:session:{phone}:signals` stores candidate signals. TTL is 30 days by default.
- **In-memory (development):** Same interface, no persistence across restarts.
- On Redis failure, the agent still works — it gracefully falls back to Postgres for signals and starts with empty transcript.

### Resume Parsing
When a candidate sends a PDF:
1. Twilio webhook extracts `MediaUrl0` and `MediaContentType0`.
2. `inbound.py` passes `media_url` and `media_type` to `run_agent_turn`.
3. Orchestrator detects PDF type and calls `parse_resume_from_url` before the LLM.
4. Extracted signals (name, role, stack, years_exp, etc.) saved immediately to Redis + Postgres.
5. LLM receives a system message: "RESUME PARSED — do NOT call parse_resume again. Extracted: {...}. React to specifics, then ask ONE follow-up question about: [missing signal]."
6. Agent never needs to call the `parse_resume` tool manually — it fires automatically.

---

## 5. The AI Agent

### Persona (System Prompt)
Mitra presents as a "well-connected friend who knows every founder in Bengaluru." Key traits:
- Sharp, warm, opinionated — not neutral
- Short messages (2–4 sentences), WhatsApp-native
- Reacts to what the candidate shares before asking the next question
- Volunteers market insight (salary benchmarks, what's in demand)
- One question per message, always
- Never sounds like a form or a checklist

### ReAct Loop
```
System prompt
+ Known signals (injected as system message)
+ Conversation transcript
+ User message
        │
        ▼
LLM decides: respond OR call tool(s)
        │
        ├─ Tool call → execute → append result → back to LLM
        └─ No tool call → final text → save → send
```

Max 8 tool rounds per turn (`MITRA_AGENT_MAX_TOOL_ROUNDS`). If hit, returns a graceful "could you tell me more?" message.

### What the Agent Collects (in order of priority)
1. **Why they're thinking of moving** — the real reason (opened here, always)
2. **What they've built** — reveals capability better than a title
3. **What they want to own next**
4. **Location / remote preference**
5. **Salary expectation** — triggers `get_salary_benchmark` immediately
6. Stack, current role, company, years of experience (collected naturally)
7. Notice period, stage preference, whether actively interviewing

---

## 6. Agent Tools

### 1. `search_jobs`
**When called:** When the agent has motivation + role type + at least one fit signal.

**Inputs:**
- `query` (required) — natural language description of what the candidate wants
- `location_hint` — e.g. `"Bengaluru"`, `"Remote India"`
- `seniority` — `intern | mid | senior | lead | principal | unknown`
- `employment_types` — array of `full_time | contract | unknown`
- `limit` — 1–8, default 5

**What it does:**
1. Gets current candidate signals from session store
2. Calls `search_jobs()` in `tools/search.py` — vector similarity search in pgvector
3. Enriches results with candidate-specific "why" blurbs via LLM reranking
4. Builds job cards with tags (employment type, remote policy, top 3 stack items)
5. Returns a JSON payload with both WhatsApp-native list rows and plain-text segments

**Output format for the agent:** JSON with `jobs` array, `whatsapp_footer`, `whatsapp_segments`, `formatted_cards`.

### 2. `remember_candidate_signals`
**When called:** Every turn where the candidate shares a new durable fact.

**Inputs:**
- `signals` — key-value map of new facts

**What it does:**
1. Writes to Redis session store immediately (fast path)
2. Writes to `candidate_signals` table in Postgres (durable path)
3. Returns `{"ok": true, "stored_keys": [...]}`

**Key signal names the agent uses:** `primary_stack`, `salary_floor_lpa`, `salary_target_lpa`, `candidate_name`, `current_role`, `current_company`, `years_experience`, `location_preference`, `notice_period_days`, `motivation`, `dealbreakers`, `startup_stage_pref`, `notable_projects`, `actively_looking`.

### 3. `get_salary_benchmark`
**When called:** The moment any salary figure is mentioned by the candidate.

**Inputs:**
- `role` — e.g. `"backend engineer"`, `"ML engineer"`
- `stage` — e.g. `"Series A"`, `"seed"`
- `seniority` — e.g. `"senior"`, `"lead"`

**What it does:** Queries `salary_benchmarks` table. Returns P25/median/P75 in LPA. Agent is instructed to always give concrete market context ("15L is below market — median for your level is 42L").

### 4. `request_intro`
**When called:** Only after the candidate explicitly confirms they want an introduction.

**Inputs:**
- `job_id` (required) — the job's `external_id` from search results
- `why_note` (required) — 1–2 sentences on why this candidate fits this role
- `candidate_name` (required)
- `primary_stack` (required) — array
- `current_role` (required)
- `current_company` (optional)

**What it does:**
1. Upserts the candidate in Postgres
2. Loads all candidate signals
3. Checks for existing intro to this job:
   - If exists AND was thin AND profile is now complete → sends enriched follow-up to founder
   - If exists AND was already complete → returns "already sent" message
4. Builds the intro message (`_build_intro`) with full candidate profile block
5. Creates `Intro` record with `status=sent`, generates `response_token` (64-char URL-safe)
6. Delivers intro to founder via:
   - WhatsApp (Twilio) if `founder_wa` is set (preferred)
   - Email (Resend) if `founder_email` is set
   - Ops inbox fallback if neither founder channel works
7. Emails BCC copy to `MITRA_OPS_EMAIL` on every successful delivery
8. If candidate used web interface (phone starts with `web:`), sends them a confirmation email

**Intro email footer** includes one-click links:
- ✅ Interested → `GET /founder/respond?token={token}&action=interested`
- ❌ Not a fit → `GET /founder/respond?token={token}&action=not_a_fit`
- 🗂 View portal → `{web_base}/founder/portal?token={founder_access_token}`

### 5. `check_intro_status`
**When called:** When candidate asks "any update?", "did they reply?", "what happened?"

**Inputs:**
- `job_id` — the job's `external_id`

**What it does:** Queries `intros` joined with `jobs` for this candidate + job. Returns status with a human-readable message per status:
- `sent` → "Waiting to hear back"
- `acknowledged` → "The founder has seen your intro"
- `interview` → "Interview booked"
- `offer` → "You have an offer"
- `hired` → "Congratulations — you joined!"
- `declined` → "Didn't move forward this time"
- `ghosted` → "No reply yet — I'll follow up"

### 6. `parse_resume`
**When called:** When the agent detects a PDF attachment (rare — usually auto-parsed before LLM turn).

**Inputs:**
- `media_url` — URL of the PDF from WhatsApp/Twilio

**What it does:** Downloads PDF, extracts text, uses LLM to extract structured signals. Saves immediately to Redis + Postgres. Returns `extracted_keys` and a summary message.

---

## 7. Founder Workflow

### Step 1: Onboarding Chat (`/founder/setup`)
Founder comes to the web and has a conversational intake chat powered by a separate LLM agent.

**The agent uses a single `respond` tool** that forces structured output every turn:
```json
{
  "message": "Your conversational reply",
  "signals": { "role_title": "Senior Backend Engineer", "salary_range": "30-45L" },
  "quick_replies": ["Full-stack", "Backend only", "ML focus"]
}
```

**Signals collected (in order):**
1. `role_title` — the role being hired for
2. `first_90_days` — what success looks like in the first 90 days
3. `dealbreaker` and/or `culture_signal` — who won't work out / what's the vibe
4. `salary_range` — compensation range
5. `company_name`, `why_join`, `stage` — company context
6. `intro_preference` — WhatsApp or email
7. `contact_info` — actual address for intro delivery

**Progress tracking:** 5 named steps (role → brief → details → context → contact) with a `%` progress bar in the UI. Completion gates at 100% once all 7 signal groups are collected.

**Fallback extraction:** If the LLM forgets to save `contact_info` from a message containing an email or phone, regex-based `_auto_extract_contact()` catches it.

**On completion:** `_auto_submit_job()` is called:
1. Builds a `JobIn` from the collected signals
2. Creates the job via `create_job()` (generates embedding)
3. Generates a `founder_access_token` (64-char secret)
4. Sends the founder a confirmation email with their portal link
5. Fires `notify_matching_candidates_bg(job.id)` as a background task

### Step 2: Founder Portal (`/founder/portal?token={access_token}`)
No login. The `founder_access_token` in the URL is the only auth mechanism.

**What the portal shows:**
- Job details (title, company, stage, location, salary, stack)
- Pipeline stats (total intros, interested, interviews, offers, hires, declined)
- Candidate cards for every intro, with full profile signals

**Auto-ghosting:** On every portal load, Mitra checks for intros in `sent` status older than 7 days and marks them `ghosted`. No cron job needed — lazy evaluation on demand.

**Progressive action buttons** based on current intro status:

| Status | Available actions |
|---|---|
| `sent` or `ghosted` | Interested ✅ · Schedule interview 📅 · Pass ❌ |
| `acknowledged` | Schedule interview 📅 · Pass ❌ |
| `interview` | Offer extended 💼 · Didn't proceed ❌ |
| `offer` | They joined! 🎉 · Offer declined ❌ |
| `hired` or `declined` | Terminal badge (no further actions) |

**On action:** `POST /founder/portal/{token}/action` with `{"intro_id": N, "action": "schedule"}`.

**Outcome tracking:** Stage timestamps are set when status transitions:
- `schedule` action → sets `interview_at` (once only)
- `offer` action → sets `offer_at` (once only)
- `hired` action → sets `hired_at` (once only)

### Founder Notifications to Candidates
When a founder takes an action, the candidate is notified. The `_ACTION_MESSAGES` dict defines the message per action:

| Action | WhatsApp subject | Message |
|---|---|---|
| `interested` | "Good news — {company} wants to connect" | Founder is interested, Mitra will coordinate |
| `not_a_fit` | "Update on your intro to {company}" | Polite "not the right fit" message |
| `schedule` | "Interview scheduled with {company}" | Interview confirmed message |
| `offer` | "{company} has extended you an offer" | Congratulations message |
| `hired` | "Congratulations — you joined {company}!" | Celebrate the hire |

**Delivery:** For WhatsApp candidates → Twilio message to their phone. For web candidates (`web:{email}`) → Resend email.

### One-Click Email Response (`GET /founder/respond`)
Founders can respond directly from the intro email without opening a portal.

- `?token={response_token}&action=interested` → sets status to `acknowledged`
- `?token={response_token}&action=not_a_fit` → sets status to `declined`

Returns a plain HTML confirmation page. No login required.

---

## 8. Intro Lifecycle

```
Candidate requests intro
        │
        ▼ (request_intro tool)
Intro record created: status=sent, response_token generated
        │
        ▼
Founder receives intro (WhatsApp or email)
        │
        ├─ One-click email link → /founder/respond?token=...&action=interested
        │   └─ status → acknowledged
        │
        └─ Founder portal → takes an action
            ├─ "Interested"          → acknowledged
            ├─ "Schedule interview"  → interview    (sets interview_at)
            ├─ "Offer extended"      → offer        (sets offer_at)
            ├─ "They joined!"        → hired         (sets hired_at)
            ├─ "Pass"/"Not a fit"    → declined
            └─ No response in 7d    → ghosted (auto, on portal load)

On every status change → candidate notified via WhatsApp or email
```

---

## 9. Proactive Job Alerts

When a job is created or its content changes materially (title, stack, summary, sector), Mitra automatically alerts matching candidates.

### Trigger
`create_job` and `update_job` admin endpoints fire `notify_matching_candidates_bg(job.id)` as a FastAPI `BackgroundTask`. The HTTP response returns immediately; the alerts go out async.

### Matching Logic (`tools/notifications.py`)
Four-gate signal match — all gates must pass:

**Gate 1: Candidate must have a stack signal**
- Checks `primary_stack`, `tech_stack`, or `stack` signal keys
- Skip if none found (incomplete profile)

**Gate 2: Stack overlap**
- If job has a defined stack, candidate must share ≥1 tech (case-insensitive)
- If job has no stack defined → gate passes automatically

**Gate 3: Salary fit**
- Candidate's `salary_target_lpa` or `salary_floor_lpa` must be ≤ job's `salary_max_lpa` × 1.2 (20% negotiation buffer)
- If either side has no salary data → gate passes

**Gate 4: Dealbreaker check**
- Candidate's `dealbreakers` list is checked against job's `sector` and `company` name
- If any dealbreaker word appears in either → skip

**Safety caps:**
- Max 30 alerts per job per run
- Candidates already intro'd to this job are skipped
- Web candidates (`phone` starts with `web:`) are skipped (WhatsApp only)

### Alert Message
Personalised WhatsApp message with:
- Job title + company in bold
- Stage / remote policy / location line
- Salary range if available
- Top 4 stack tags
- A "why_line" explaining the match (stack overlap, stage preference, or general fit)
- Call-to-action: "Interested? Just message me back and I'll make the intro."

---

## 10. Admin System

### Authentication
All `/admin/*` endpoints require `X-Admin-Key` header matching `MITRA_ADMIN_KEY` env var.

### Job CRUD (`/admin/jobs/*`)

| Endpoint | What it does |
|---|---|
| `POST /admin/jobs` | Create job, generate embedding, fire alerts |
| `GET /admin/jobs?status=active` | List jobs filtered by status |
| `PUT /admin/jobs/{id}` | Update job; regenerates embedding + re-alerts if content changed |
| `DELETE /admin/jobs/{id}` | Soft-delete (marks as `expired`) |
| `POST /admin/jobs/seed` | Bulk-seed from `data/jobs.json` (skips duplicates by `external_id`) |

**Embedding generation:** `job_embed_text()` builds a string from title + sector + stage + stack + summary + location. Embedded via Voyage AI or OpenAI. Stored in `job_embeddings` as a pgvector `vector` column.

### Metrics Endpoint (`GET /admin/metrics`)
Returns `MetricsResponse`:

```typescript
{
  snapshot: {
    total_candidates: number,
    total_jobs:       number,
    active_jobs:      number,
    total_intros:     number,
  },
  funnel: FunnelStage[],         // sent → acknowledged → interview → offer → hired
  by_status: Record<string, int>, // all 7 statuses with counts
  weekly_trend: WeeklyPoint[],   // last 8 weeks: intros + interviews + hires per week
  top_jobs: TopJob[],            // top 6 jobs by intro volume with hire rates
  response_rate: number,         // % of intros that got any positive response
  ghosted_rate: number,          // % of intros that ghosted
  avg_days_to_interview: number | null,
  avg_days_to_hire: number | null,
}
```

### Candidate Reset (`DELETE /admin/candidates/{phone}/reset`)
Wipes all data for a candidate — Redis session + Postgres rows (cascade deletes signals and intros). Used for test resets.

### Debug Endpoints
- `POST /debug/agent?message=...&session_id=...` — test the full agent loop without WhatsApp
- `POST /debug/llm` — test LLM connectivity (sends "Reply with one word: ready")

---

## 11. Frontend Pages

### `/` — Landing page
Marketing / home page.

### `/chat` — Web candidate interface
`MitraChat.tsx` — web-based version of the WhatsApp chat. Candidate interacts via browser instead of WhatsApp. Uses the same agent backend.

### `/onboarding` — Candidate web onboarding
Web-based candidate intake form.

### `/matches` and `/dashboard` — Candidate views
`MatchesView.tsx`, `MatchesPanelClient.tsx`, `IntrosPanelClient.tsx` — candidate dashboard showing their matches and intro statuses.

### `/founder/setup` — Founder onboarding
`TokenInput.tsx` — the conversational onboarding chat for founders. Collects job details, generates the founder's access token, sends portal link.

### `/founder/portal?token={token}` — Founder pipeline portal
`FounderPortalClient.tsx` — no-login candidate pipeline view. Shows all intros for the founder's job with progressive action buttons and status tracking.

**Status display:**
| Status | Label | Color |
|---|---|---|
| `sent` | New introduction | Teal |
| `acknowledged` | Interested | Purple |
| `interview` | Interview set | Amber |
| `offer` | Offer extended | Blue |
| `hired` | Hired | Green |
| `declined` | Not a fit | Grey |
| `ghosted` | Awaiting reply | Light grey |

### `/admin` — Ops metrics dashboard
`MetricsDashboard.tsx` — dark-theme internal dashboard (not visible to candidates or founders). Gated by admin key prompt (stored in `sessionStorage`).

**Components:**
- `KeyGate` — password prompt, stored in sessionStorage (clears on tab close)
- `KpiCard` — 4 KPI tiles: Total Intros, Hired (green accent), Conversion Rate, Active Jobs
- `FunnelBar` — horizontal bar chart of the hiring funnel (blue→purple→amber→orange→green)
- `StatPill` — Pipeline Health stats: response rate, ghost rate, avg days to interview/hire
- `StatusGrid` — 7-cell breakdown of all intro statuses
- `WeeklyChart` — pure SVG bar chart, last 8 weeks. Dark bars = intros, bright green overlay = hires, amber line = interviews
- `TopJobsTable` — top 6 roles by intro volume with hire rate badges
- `Skeleton` — loading state placeholder

Refresh button in top-right re-fetches metrics. Timestamp shows last update time.

---

## 12. Infrastructure & Config

### Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `MITRA_LLM_PROVIDER` | Yes | `anthropic` or `openai` |
| `MITRA_LLM_MODEL` | Yes | e.g. `claude-sonnet-4-20250514` |
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | Yes | Depends on provider |
| `MITRA_DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `MITRA_ADMIN_KEY` | Yes | Any strong secret for /admin/* |
| `MITRA_EMBEDDING_PROVIDER` | Yes | `voyage` (recommended) or `openai` |
| `VOYAGE_API_KEY` | If voyage | |
| `MITRA_REDIS_URL` | Prod | `redis://host:6379/0` — in-memory if empty |
| `WHATSAPP_VERIFY_TOKEN` | If Meta | |
| `WHATSAPP_ACCESS_TOKEN` | If Meta | |
| `WHATSAPP_PHONE_NUMBER_ID` | If Meta | |
| `WHATSAPP_APP_SECRET` | If Meta | HMAC signature verification |
| `TWILIO_ACCOUNT_SID` | If Twilio | |
| `TWILIO_AUTH_TOKEN` | If Twilio | |
| `TWILIO_WHATSAPP_FROM` | If Twilio | e.g. `whatsapp:+14155238886` |
| `MITRA_TWILIO_WEBHOOK_URL` | If Twilio | Exact public URL for signature check |
| `RESEND_API_KEY` | Yes (email) | |
| `MITRA_FROM_EMAIL` | Yes (email) | Verified sender address |
| `MITRA_OPS_EMAIL` | Recommended | BCC inbox for every intro |
| `MITRA_API_BASE_URL` | Yes | Public URL of this FastAPI server |
| `MITRA_WEB_BASE_URL` | Yes | Public URL of Next.js app |
| `MITRA_WHATSAPP_NATIVE_LIST` | Optional | `true` = interactive list picker |
| `MITRA_AGENT_MAX_TOOL_ROUNDS` | Optional | Default 8 |
| `MITRA_SESSION_TTL_SECONDS` | Optional | Default 30 days |

### Database Migrations
Run `python -m mitra_api.db.migrations` on startup or after schema changes. Uses `ADD COLUMN IF NOT EXISTS` — idempotent and safe to re-run. Also run automatically on app startup via the `lifespan` handler.

### Startup Sequence (`lifespan` in `main.py`)
1. Run schema migrations (idempotent)
2. Yield (app is live)
3. On shutdown: close session store → dispose SQLAlchemy engine

### Health Endpoints
- `GET /healthz` → `"ok"` (simple liveness check)
- `GET /readyz` → JSON with `llm` and `db` connectivity status (for readiness probes)

---

*Last updated: May 2026. This document covers all features implemented as of the current codebase.*



