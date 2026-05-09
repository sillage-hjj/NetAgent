import pytest

from netfabric_mini.llm.config import load_llm_config, redacted_diagnostics, resolve_provider


def test_default_config_uses_mock(monkeypatch) -> None:
    monkeypatch.delenv("NFM_AGENT_PROVIDER", raising=False)

    config = load_llm_config()

    assert config.provider == "mock"
    assert config.model == "mock-agent"


def test_env_overrides_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NFM_AGENT_PROVIDER", "mock")
    monkeypatch.setenv("NFM_AGENT_MAX_TOOL_CALLS", "3")
    monkeypatch.setenv("NFM_AGENT_REQUIRE_EVIDENCE", "false")

    config = load_llm_config()

    assert config.max_tool_calls == 3
    assert config.require_evidence is False


def test_openai_config_requires_key(monkeypatch) -> None:
    monkeypatch.setenv("NFM_AGENT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = load_llm_config()

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        resolve_provider(config)


def test_secrets_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    config = load_llm_config()

    assert "sk-secret" not in str(redacted_diagnostics(config))

