# Mitra API (WhatsApp agent)

FastAPI service that receives **WhatsApp Cloud API** webhooks and runs an **agentic pipeline**: tool-using LLM loop with **`search_jobs`** and **`remember_candidate_signals`**. The LLM backend is **config-only switchable** between **OpenAI** and **Anthropic** (`MITRA_LLM_PROVIDER` + `MITRA_LLM_MODEL` + the matching API key).

## Requirements

- Python 3.11+
- Credentials: OpenAI **or** Anthropic; WhatsApp ingress via **Meta Cloud API** and/or **Twilio WhatsApp** (sandbox-friendly).

## Setup

From `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy .env.example .env   # edit .env — use setx / export on CI as needed
```

## Run

```bash
uvicorn mitra_api.main:app --host 0.0.0.0 --port 8080 --reload
```

- WhatsApp webhook — **choose one or both:**
  - **Meta Cloud API**: `GET/POST https://<host>/webhook/whatsapp`
    - Meta sends query params **`hub.mode`**, **`hub.verify_token`**, **`hub.challenge`** on subscribe; wired in code.
  - **Twilio WhatsApp (sandbox/testing)**: `POST https://<host>/webhook/twilio/whatsapp`
    - No Meta Developer app needed for sandbox; Twilio WhatsApp Sandbox issues the join-code flow.

## Environment

See `.env.example`. Summary:

| Variable | Meaning |
|---------|---------|
| `MITRA_LLM_PROVIDER` | `openai` or `anthropic` |
| `MITRA_LLM_MODEL` | Provider model id |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Active provider API key |
| `WHATSAPP_VERIFY_TOKEN` | Must match Meta callback verify token |
| `WHATSAPP_ACCESS_TOKEN` | Graph API permanent/temporary token |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone number ID for outbound messages |
| `WHATSAPP_APP_SECRET` | If set, validates `X-Hub-Signature-256` |
| `TWILIO_ACCOUNT_SID` | Twilio Console Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (used for outbound + signature validation) |
| `TWILIO_WHATSAPP_FROM` | e.g. `whatsapp:+14155238886` (sandbox) |
| `MITRA_TWILIO_WEBHOOK_URL` | Exact HTTPS URL Twilio calls (path included); fixes signature behind ngrok |
| `MITRA_TWILIO_VALIDATE_WEBHOOK` | `true`/`false` — set `false` only if URL/signature debugging |
| `MITRA_WHATSAPP_NATIVE_LIST` | `true`: job recommendations use WhatsApp **interactive list** (tap menu). `false`: legacy long text slabs only. |
| `MITRA_REDIS_URL` | e.g. `redis://localhost:6379/0` — **persistent** chat transcripts + tool signals per sender; leave empty for in-memory (dev only). |
| `MITRA_SESSION_TTL_SECONDS` | Redis expiry for session keys (refreshed on each message). |
| `MITRA_REDIS_KEY_PREFIX` | Namespace prefix for Redis keys. |
| `TAVILY_API_KEY` | **Optional** — enables `web_market_research` (live web search via [Tavily](https://tavily.com)). Leave empty to disable. |
| `MITRA_TAVILY_SEARCH_DEPTH` | `basic` or `advanced` (default `advanced`) — Tavily quota vs. richness tradeoff. |
| `MITRA_MARKET_RESEARCH_MAX_RESULTS` | Web hits per call, 1–10 (default `5`). |

### Twilio sandbox (quick test)

1. Create a free Twilio account → **Messaging** → **Try it out** → **Send a WhatsApp message** (sandbox).
2. Join the sandbox from your phone with the printed code.
3. Expose this API with HTTPS (ngrok): set `MITRA_TWILIO_WEBHOOK_URL` to `https://<tunnel>/webhook/twilio/whatsapp`.
4. In Twilio, set **When a message comes in** (sandbox webhook) to that same URL, method **HTTP POST**.
5. Fill `TWILIO_*` in `.env`; keep `TWILIO_WHATSAPP_FROM` as the sandbox sender (`whatsapp:+14155238886`).

### Optional: HTTPS tunnel for local webhook testing

Use ngrok/cloudflared/etc. pointing at `:8080` and paste the HTTPS URL into **Meta** or **Twilio** webhook settings.

## Debug endpoints
- `GET /readyz` — verifies LLM factory can instantiate (still does not ping OpenAI/Anthropic)
- `POST /debug/agent?message=...&session_id=...` — one agent turn (no WhatsApp)
- `POST /debug/llm` — one completion (+ tools) smoke test (**may incur billing**)

## Architecture

- **`mitra_api/llm/`** — canonical `ChatMessage` / tools; adapters for OpenAI Chat Completions and Anthropic Messages; `get_llm_adapter()` selects by env.
- **`mitra_api/agent/`** — ReAct-style loop in `run_agent_turn`: assistant may call tools; runner executes Python functions; repeats until assistant returns text-only (bounded by `MITRA_AGENT_MAX_TOOL_ROUNDS`).
- **`mitra_api/whatsapp/meta_interactive.py`** — WhatsApp Cloud **interactive list** messages (native sheet UI).
- **`mitra_api/twilio_whatsapp/list_picker.py`** — Twilio Content API **list-picker** for the same UX on Twilio WhatsApp.
- **`mitra_api/twilio_whatsapp/`** — Twilio form POST webhook + REST `Messages.json` reply.
- **`mitra_api/inbound.py`** — shared `run_agent_reply` for both channels.
- **Sessions** — `AgentSessionStore`: set `MITRA_REDIS_URL` for **Redis**-backed transcripts + merged candidate signals; otherwise in-memory (single-process only).
- **Demo jobs** — curated list in `mitra_api/data/jobs.json` (loaded at import); swap the file or wire your own index later.

## Next steps (typical)

- Extend Redis keys or add Postgres for analytics / multi-tenant isolation.
- Replace the JSON job file with real search (vector + filters, or external ATS).
- Queue long agent runs (Celery / Cloud Tasks) if turns exceed WhatsApp response windows; use typing indicators / follow-up messages.
