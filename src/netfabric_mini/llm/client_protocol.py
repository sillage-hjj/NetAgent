from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class LLMModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LLMMessage(LLMModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class LLMToolSpec(LLMModel):
    name: str
    description: str
    parameters_json_schema: dict[str, Any]
    read_only: bool
    requires_approval: bool = False


class LLMToolCall(LLMModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(LLMModel):
    id: str
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    structured_output: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw_provider_response: dict[str, Any] | None = None


class LLMClientProtocol(Protocol):
    def create_response(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        response_schema: dict[str, Any] | None,
        previous_response_id: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        ...

