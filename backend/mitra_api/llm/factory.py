import logging

from mitra_api.config import Settings, get_settings
from mitra_api.llm.adapters.anthropic_adapter import AnthropicAdapter
from mitra_api.llm.adapters.base import LLMAdapter
from mitra_api.llm.adapters.openai_adapter import OpenAIAdapter

log = logging.getLogger(__name__)


def get_llm_adapter(settings: Settings | None = None) -> LLMAdapter:
    s = settings or get_settings()
    if s.mitra_llm_provider == "openai":
        if not s.openai_api_key.strip():
            raise RuntimeError("OPENAI_API_KEY is required when MITRA_LLM_PROVIDER=openai")
        return OpenAIAdapter(api_key=s.openai_api_key)
    if s.mitra_llm_provider == "anthropic":
        if not s.anthropic_api_key.strip():
            raise RuntimeError("ANTHROPIC_API_KEY is required when MITRA_LLM_PROVIDER=anthropic")
        return AnthropicAdapter(api_key=s.anthropic_api_key)
    raise RuntimeError(f"Unknown MITRA_LLM_PROVIDER: {s.mitra_llm_provider}")
