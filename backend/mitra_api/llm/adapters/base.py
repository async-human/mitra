from abc import ABC, abstractmethod

from mitra_api.llm.types import ChatMessage, LLMResult, ToolDefinition


class LLMAdapter(ABC):
    """Vendor-neutral completion API (chat + optional tools)."""

    @abstractmethod
    async def complete(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None,
        max_tokens: int,
        temperature: float,
        force_tool: str | None = None,
    ) -> LLMResult:
        """Complete a chat turn.

        Args:
            force_tool: When set, instructs the provider to call this specific
                tool (Anthropic: tool_choice type=tool; OpenAI: tool_choice
                type=function). Callers that don't need this can omit it.
        """
        raise NotImplementedError
