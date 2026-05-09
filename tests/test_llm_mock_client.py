import json
from typing import cast

from netfabric_mini.llm.client_protocol import LLMClientProtocol, LLMMessage, LLMResponse, LLMToolCall
from netfabric_mini.llm.mock_client import MockLLMClient


def test_mock_client_implements_protocol_and_returns_scripted_calls() -> None:
    client = cast(LLMClientProtocol, MockLLMClient("link_failure"))

    response = client.create_response(messages=[LLMMessage(role="user", content="why")], tools=[], response_schema=None)

    assert response.tool_calls
    assert response.tool_calls[0].name == "run_monitoring_cycle"
    json.dumps(response.model_dump(mode="json"))


def test_mock_client_can_return_final_structured_output() -> None:
    client = MockLLMClient(responses=[LLMResponse(id="r1", structured_output={"ok": True}, tool_calls=[])])

    response = client.create_response(messages=[], tools=[], response_schema=None)

    assert response.structured_output == {"ok": True}

