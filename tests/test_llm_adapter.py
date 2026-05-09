import inspect

from netagent_lab.db import init_db
from netagent_lab.llm_adapter import MockLLMAdapter
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.seed_loader import load_case


def test_mock_llm_adapter_returns_investigation_result() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")
    parse_and_store_all(conn)

    result = MockLLMAdapter().investigate(conn, "T-001")

    assert result["ticket_id"] == "T-001"
    assert result["root_cause_type"] == "acl_block"
    assert result["evidence"]


def test_llm_adapter_makes_no_network_or_external_api_calls() -> None:
    import netagent_lab.llm_adapter as llm_adapter

    source = inspect.getsource(llm_adapter)

    assert "requests" not in source
    assert "httpx" not in source
    assert "openai" not in source.lower()
    assert "socket" not in source

