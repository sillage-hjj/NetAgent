from __future__ import annotations

import json
from typing import Any

from netagent_lab.llm.client_protocol import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec
from netagent_lab.llm.config import LLMProviderConfig


class OpenAIResponsesClient:
    def __init__(self, config: LLMProviderConfig, client: Any | None = None):
        self.config = config
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError("OpenAI provider requires installing netagent-lab[llm] or the official openai package.") from exc
        self._client = OpenAI()
        return self._client

    def create_response(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        response_schema: dict[str, Any] | None,
        previous_response_id: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        if not hasattr(self.client, "responses"):
            raise RuntimeError("Installed OpenAI SDK does not expose client.responses; update the openai package.")
        instructions = "\n\n".join(message.content for message in messages if message.role == "system")
        input_messages = [message for message in messages if message.role != "system"]
        kwargs: dict[str, Any] = {
            "input": [_message_to_input(message) for message in input_messages],
            "tools": [_tool_to_openai(tool) for tool in tools],
            "max_output_tokens": max_output_tokens or self.config.max_output_tokens,
            "parallel_tool_calls": False,
            "store": False,
        }
        if instructions:
            kwargs["instructions"] = instructions
        if self.config.model:
            kwargs["model"] = self.config.model
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if response_schema:
            schema, strict = _prepare_response_schema(response_schema)
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "agent_report",
                    "schema": schema,
                    "strict": strict,
                }
            }
        try:
            provider_response = self.client.responses.create(**kwargs)
        except AttributeError as exc:
            raise RuntimeError("OpenAI Responses API is unavailable in the installed SDK.") from exc
        except Exception as exc:
            raise RuntimeError(f"OpenAI Responses API request failed safely: {exc.__class__.__name__}") from exc
        return _normalize_response(provider_response)


def _message_to_input(message: LLMMessage) -> dict[str, Any]:
    if message.role == "tool":
        return {
            "type": "function_call_output",
            "call_id": message.tool_call_id or message.name or "tool-call",
            "output": message.content,
        }
    payload = {"role": message.role, "content": message.content}
    if message.name:
        payload["name"] = message.name
    return payload


def _tool_to_openai(tool: LLMToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters_json_schema,
        "strict": False,
    }


def _prepare_response_schema(schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    sanitized = _sanitize_schema(schema)
    return sanitized, _is_strict_compatible(sanitized)


def _sanitize_schema(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"title", "default", "examples"}:
                continue
            sanitized[key] = _sanitize_schema(item)
        if sanitized.get("type") == "object" and "additionalProperties" not in sanitized:
            sanitized["additionalProperties"] = False
        return sanitized
    if isinstance(value, list):
        return [_sanitize_schema(item) for item in value]
    return value


def _is_strict_compatible(schema: Any) -> bool:
    if isinstance(schema, dict):
        if any(key in schema for key in {"anyOf", "oneOf", "allOf", "not"}):
            return False
        if "$defs" in schema:
            return False
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            required = set(schema.get("required", []))
            if isinstance(properties, dict) and set(properties) != required:
                return False
        return all(_is_strict_compatible(value) for value in schema.values())
    if isinstance(schema, list):
        return all(_is_strict_compatible(item) for item in schema)
    return True


def _normalize_response(response: Any) -> LLMResponse:
    response_id = str(_get(response, "id", "openai-response"))
    content = _get(response, "output_text", None) or _extract_text(response)
    tool_calls: list[LLMToolCall] = []
    structured_output = _extract_structured_output(response, content)
    for item in _iter_output_items(response):
        item_type = _get(item, "type", None)
        if item_type in {"function_call", "tool_call"}:
            name = _get(item, "name", None)
            call_id = _get(item, "call_id", None) or _get(item, "id", None)
            arguments = _get(item, "arguments", "{}")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise RuntimeError("OpenAI Responses API returned malformed tool-call arguments.") from exc
            tool_calls.append(LLMToolCall(id=str(call_id), name=name, arguments=arguments))
    usage = _usage_dict(_get(response, "usage", None), response)
    raw = response.model_dump(mode="json") if hasattr(response, "model_dump") else None
    return LLMResponse(
        id=response_id,
        content=content,
        tool_calls=tool_calls,
        structured_output=structured_output,
        usage=usage,
        raw_provider_response=raw,
    )


def _iter_output_items(response: Any) -> list[Any]:
    output = _get(response, "output", []) or []
    items = list(output)
    for item in output:
        for content_item in _get(item, "content", []) or []:
            items.append(content_item)
    return items


def _extract_text(response: Any) -> str | None:
    texts: list[str] = []
    for item in _iter_output_items(response):
        item_type = _get(item, "type", None)
        if item_type in {"output_text", "text"}:
            text = _get(item, "text", None)
            if isinstance(text, str):
                texts.append(text)
    return "\n".join(texts) if texts else None


def _extract_structured_output(response: Any, content: str | None) -> dict[str, Any] | None:
    for item in _iter_output_items(response):
        parsed = _get(item, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
    if content:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _usage_dict(usage: Any, response: Any | None = None) -> dict[str, Any]:
    if usage is None:
        data: dict[str, Any] = {}
    elif isinstance(usage, dict):
        data = dict(usage)
    elif hasattr(usage, "model_dump"):
        data = usage.model_dump(mode="json")
    else:
        data = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
    normalized = dict(data)
    input_details = _get(usage, "input_tokens_details", None) or _get(usage, "input_details", None) or {}
    output_details = _get(usage, "output_tokens_details", None) or _get(usage, "output_details", None) or {}
    cached = _get(input_details, "cached_tokens", None)
    reasoning = _get(output_details, "reasoning_tokens", None) or _get(usage, "reasoning_tokens", None)
    if cached is not None:
        normalized["cached_tokens"] = cached
    if reasoning is not None:
        normalized["reasoning_tokens"] = reasoning
    if response is not None:
        model = _get(response, "model", None)
        if model is not None:
            normalized["model"] = model
    return {key: value for key, value in normalized.items() if value is not None}
