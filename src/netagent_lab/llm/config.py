from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from netagent_lab.llm.client_protocol import LLMClientProtocol


DEFAULT_OPENAI_MODEL = "gpt-5-mini"


class LLMProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock", "openai"] = "mock"
    model: str | None = None
    max_tool_calls: int = Field(default=8, ge=0)
    max_output_tokens: int = Field(default=1200, ge=1)
    temperature: float = Field(default=0.0, ge=0, le=2)
    require_evidence: bool = True
    allow_sim_mutation: bool = False
    max_context_events: int = Field(default=50, ge=0)
    max_context_telemetry: int = Field(default=100, ge=0)
    timeout_seconds: float = Field(default=30.0, gt=0)

    def __repr__(self) -> str:
        return self.model_dump_json()


def load_llm_config() -> LLMProviderConfig:
    provider = os.getenv("NFM_AGENT_PROVIDER", "mock").lower()
    if provider not in {"mock", "openai"}:
        raise ValueError("NFM_AGENT_PROVIDER must be 'mock' or 'openai'")
    model = os.getenv("OPENAI_MODEL") or (DEFAULT_OPENAI_MODEL if provider == "openai" else "mock-agent")
    return LLMProviderConfig(
        provider=provider,  # type: ignore[arg-type]
        model=model,
        max_tool_calls=_int_env("NFM_AGENT_MAX_TOOL_CALLS", 8),
        max_output_tokens=_int_env("NFM_AGENT_MAX_OUTPUT_TOKENS", 1200),
        temperature=_float_env("NFM_AGENT_TEMPERATURE", 0.0),
        require_evidence=_bool_env("NFM_AGENT_REQUIRE_EVIDENCE", True),
        allow_sim_mutation=_bool_env("NFM_AGENT_ALLOW_SIM_MUTATION", False),
        max_context_events=_int_env("NFM_AGENT_MAX_CONTEXT_EVENTS", 50),
        max_context_telemetry=_int_env("NFM_AGENT_MAX_CONTEXT_TELEMETRY", 100),
        timeout_seconds=_float_env("NFM_AGENT_TIMEOUT_SECONDS", 30.0),
    )


def resolve_provider(config: LLMProviderConfig) -> LLMClientProtocol:
    if config.provider == "mock":
        from netagent_lab.llm.mock_client import MockLLMClient

        return MockLLMClient()
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("NFM_AGENT_PROVIDER=openai requires OPENAI_API_KEY")
    from netagent_lab.llm.openai_client import OpenAIResponsesClient

    return OpenAIResponsesClient(config)


def redacted_diagnostics(config: LLMProviderConfig) -> dict[str, object]:
    return {
        "provider": config.provider,
        "model": config.model,
        "max_tool_calls": config.max_tool_calls,
        "max_output_tokens": config.max_output_tokens,
        "temperature": config.temperature,
        "require_evidence": config.require_evidence,
        "allow_sim_mutation": config.allow_sim_mutation,
        "max_context_events": config.max_context_events,
        "max_context_telemetry": config.max_context_telemetry,
        "timeout_seconds": config.timeout_seconds,
        "openai_api_key": "<redacted>" if os.getenv("OPENAI_API_KEY") else "<unset>",
    }


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default

