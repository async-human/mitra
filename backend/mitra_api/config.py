"""
mitra_api/config.py  (updated for production)

Adds:
  - MITRA_DATABASE_URL   (PostgreSQL + asyncpg)
  - MITRA_ADMIN_KEY      (protects /admin/* endpoints)
  - MITRA_EMBEDDING_PROVIDER (voyage or openai)
  - VOYAGE_API_KEY       (optional — for voyage-3 embeddings)

All existing settings unchanged — drop-in replacement.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mitra_api_host: str = Field(default="0.0.0.0", validation_alias="MITRA_API_HOST")
    mitra_api_port: int = Field(default=8080,       validation_alias="MITRA_API_PORT")

    # ── LLM ──────────────────────────────────────────────────────────────────
    mitra_llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        validation_alias="MITRA_LLM_PROVIDER",
    )
    mitra_llm_model: str    = Field(default="gpt-4o-mini", validation_alias="MITRA_LLM_MODEL")
    mitra_llm_max_tokens: int   = Field(default=2048, validation_alias="MITRA_LLM_MAX_TOKENS")
    mitra_llm_temperature: float = Field(default=0.2, validation_alias="MITRA_LLM_TEMPERATURE")

    openai_api_key:    str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # ── DATABASE ──────────────────────────────────────────────────────────────
    mitra_database_url: str = Field(
        default="",
        validation_alias="MITRA_DATABASE_URL",
        description=(
            "Async PostgreSQL URL. "
            "Format: postgresql+asyncpg://user:pass@host:5432/dbname "
            "Supabase example: postgresql+asyncpg://postgres:[password]@db.[project].supabase.co:5432/postgres"
        ),
    )

    # ── EMBEDDINGS ────────────────────────────────────────────────────────────
    mitra_embedding_provider: Literal["voyage", "openai"] = Field(
        default="openai",
        validation_alias="MITRA_EMBEDDING_PROVIDER",
        description="voyage (recommended) or openai. voyage-3 gives better semantic job matching.",
    )
    voyage_api_key: str = Field(
        default="",
        validation_alias="VOYAGE_API_KEY",
        description="Required when MITRA_EMBEDDING_PROVIDER=voyage. Get free key at voyageai.com.",
    )

    # ── ADMIN ─────────────────────────────────────────────────────────────────
    mitra_admin_key: str = Field(
        default="",
        validation_alias="MITRA_ADMIN_KEY",
        description="Secret key for /admin/* endpoints. Set to any strong random string.",
    )

    # ── AGENT ─────────────────────────────────────────────────────────────────
    mitra_agent_max_tool_rounds: int = Field(default=8, validation_alias="MITRA_AGENT_MAX_TOOL_ROUNDS")

    # ── SESSION STORE (Redis) ─────────────────────────────────────────────────
    mitra_redis_url: str = Field(
        default="",
        validation_alias="MITRA_REDIS_URL",
        description="redis://host:port/0 — leave empty for in-memory (dev only).",
    )
    mitra_session_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 30,
        validation_alias="MITRA_SESSION_TTL_SECONDS",
    )
    mitra_redis_key_prefix: str = Field(
        default="mitra",
        validation_alias="MITRA_REDIS_KEY_PREFIX",
    )

    # ── WHATSAPP (Meta Cloud) ─────────────────────────────────────────────────
    whatsapp_verify_token:   str = Field(default="", validation_alias="WHATSAPP_VERIFY_TOKEN")
    whatsapp_access_token:   str = Field(default="", validation_alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(default="", validation_alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_app_secret:     str = Field(default="", validation_alias="WHATSAPP_APP_SECRET")

    # ── TWILIO ────────────────────────────────────────────────────────────────
    twilio_account_sid:  str = Field(default="", validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token:   str = Field(default="", validation_alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(default="", validation_alias="TWILIO_WHATSAPP_FROM")
    mitra_twilio_validate_webhook: bool = Field(
        default=True, validation_alias="MITRA_TWILIO_VALIDATE_WEBHOOK"
    )
    mitra_twilio_webhook_url: str = Field(
        default="", validation_alias="MITRA_TWILIO_WEBHOOK_URL"
    )
    mitra_whatsapp_native_list: bool = Field(
        default=False,
        validation_alias="MITRA_WHATSAPP_NATIVE_LIST",
        description="Set true to use interactive list picker. False = inline plain-text cards.",
    )

    # ── WEB MARKET RESEARCH (Tavily) ───────────────────────────────────────────
    tavily_api_key: str = Field(
        default="",
        validation_alias="TAVILY_API_KEY",
        description=(
            "Tavily Search API key for web_market_research tool — live snippets from the public web. "
            "https://tavily.com — leave empty to disable (agent falls back to get_salary_benchmark only)."
        ),
    )
    mitra_tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        validation_alias="MITRA_TAVILY_SEARCH_DEPTH",
        description="Tavily search depth — advanced uses more quota but fresher/richer results.",
    )
    mitra_market_research_max_results: int = Field(
        default=5,
        validation_alias="MITRA_MARKET_RESEARCH_MAX_RESULTS",
        ge=1,
        le=10,
        description="Max web results per web_market_research call (1–10).",
    )

    # ── EMAIL (Resend) ────────────────────────────────────────────────────────
    resend_api_key: str = Field(
        default="",
        validation_alias="RESEND_API_KEY",
        description="Resend API key — used to email intro notes to founders. Get one at resend.com.",
    )
    mitra_from_email: str = Field(
        default="",
        validation_alias="MITRA_FROM_EMAIL",
        description="Verified sender address for Resend (e.g. intros@yourdomain.com).",
    )
    mitra_ops_email: str = Field(
        default="",
        validation_alias="MITRA_OPS_EMAIL",
        description=(
            "Ops/team inbox that receives intro copies when a job has no founder contact channel. "
            "Also receives a BCC of every intro sent directly to a founder."
        ),
    )
    mitra_api_base_url: str = Field(
        default="http://localhost:8080",
        validation_alias="MITRA_API_BASE_URL",
        description="Public base URL of this API server — used to build founder response links in emails.",
    )
    mitra_web_base_url: str = Field(
        default="http://localhost:3000",
        validation_alias="MITRA_WEB_BASE_URL",
        description="Public base URL of the Next.js web app — used to build founder portal links in emails.",
    )
    email_webhook_secret: str = Field(
        default="",
        validation_alias="EMAIL_WEBHOOK_SECRET",
        description="Shared secret between Cloudflare Email Worker and this API — validates inbound email webhooks.",
    )

    # ── SCHEDULING (Cal.com) ──────────────────────────────────────────────────
    cal_booking_url: str = Field(
        default="",
        validation_alias="CAL_BOOKING_URL",
        description=(
            "Base URL of your Cal.com event type, e.g. https://cal.com/mitra/intro-call. "
            "When set, candidate scheduling emails include a self-service booking link. "
            "Leave empty to fall back to email-based slot coordination."
        ),
    )
    cal_webhook_secret: str = Field(
        default="",
        validation_alias="CAL_WEBHOOK_SECRET",
        description=(
            "HMAC secret configured in Cal.com → Settings → Webhooks. "
            "Used to validate incoming booking confirmation webhooks."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
