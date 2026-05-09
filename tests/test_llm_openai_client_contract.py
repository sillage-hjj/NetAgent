import json
from typing import cast

import pytest

from netfabric_mini.llm.client_protocol import LLMClientProtocol, LLMMessage, LLMToolSpec
from netfabric_mini.llm.config import LLMProviderConfig
from netfabric_mini.llm.openai_client import OpenAIResponsesClient


class FakeResponses:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return {
            "id": "resp-1",
            "model": "fake-model",
            "output_text": '{"ok": true}',
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call-1",
                    "name": "get_current_context",
                    "arguments": "{}",
                }
            ],
            "usage": {
                "input_tokens": 1,
                "output_tokens": 2,
                "input_tokens_details": {"cached_tokens": 3},
                "output_tokens_details": {"reasoning_tokens": 4},
            },
        }


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_client_implements_protocol_and_parses_tool_calls() -> None:
    client = cast(
        LLMClientProtocol,
        OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"), client=FakeClient()),
    )

    response = client.create_response(
        messages=[LLMMessage(role="user", content="hi")],
        tools=[
            LLMToolSpec(
                name="get_current_context",
                description="ctx",
                parameters_json_schema={"type": "object", "properties": {}},
                read_only=True,
            )
        ],
        response_schema={"type": "object"},
    )

    assert response.id == "resp-1"
    assert response.tool_calls[0].name == "get_current_context"
    assert response.structured_output == {"ok": True}
    assert response.usage["input_tokens"] == 1
    assert response.usage["cached_tokens"] == 3
    assert response.usage["reasoning_tokens"] == 4
    assert response.usage["model"] == "fake-model"
    json.dumps(response.model_dump(mode="json"))
    assert client.client.responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert client.client.responses.kwargs["tools"][0]["type"] == "function"


def test_openai_client_converts_tool_result_messages() -> None:
    fake = FakeClient()
    client = OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"), client=fake)

    client.create_response(
        messages=[LLMMessage(role="tool", content='{"ok": true}', tool_call_id="call-1")],
        tools=[],
        response_schema=None,
    )

    assert fake.responses.kwargs["input"][0] == {
        "type": "function_call_output",
        "call_id": "call-1",
        "output": '{"ok": true}',
    }


def test_openai_client_parses_nested_output_text_and_parsed_payload() -> None:
    class NestedResponses:
        def create(self, **kwargs):
            return {
                "id": "resp-2",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": '{"answer_type": "state_explanation"}'},
                            {"type": "output_text", "parsed": {"answer_type": "state_explanation"}},
                        ],
                    }
                ],
                "usage": {"input_tokens": 2, "output_tokens": 3},
            }

    class NestedClient:
        responses = NestedResponses()

    client = OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"), client=NestedClient())

    response = client.create_response(messages=[], tools=[], response_schema={"type": "object"})

    assert response.content == '{"answer_type": "state_explanation"}'
    assert response.structured_output == {"answer_type": "state_explanation"}


def test_openai_client_missing_sdk_fails_only_when_used(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    client = OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"))

    with pytest.raises(RuntimeError, match="official openai package"):
        _ = client.client


def test_openai_client_missing_responses_fails_clearly() -> None:
    client = OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"), client=object())

    with pytest.raises(RuntimeError, match="client.responses"):
        client.create_response(messages=[], tools=[], response_schema=None)


def test_openai_provider_errors_are_wrapped_safely() -> None:
    class BrokenResponses:
        def create(self, **kwargs):
            raise ValueError("secret should not be echoed")

    class BrokenClient:
        responses = BrokenResponses()

    client = OpenAIResponsesClient(LLMProviderConfig(provider="openai", model="test-model"), client=BrokenClient())

    with pytest.raises(RuntimeError) as exc:
        client.create_response(messages=[], tools=[], response_schema=None)

    assert "ValueError" in str(exc.value)
    assert "secret should not be echoed" not in str(exc.value)
