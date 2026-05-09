from netagent_lab.agent.prompts import build_system_prompt
from netagent_lab.llm.config import LLMProviderConfig


def test_system_prompt_contains_safety_requirements() -> None:
    prompt = build_system_prompt(LLMProviderConfig())

    assert "Cite evidence IDs" in prompt
    assert "Never invent topology" in prompt
    assert "Never claim that a remediation was executed" in prompt
    assert "OPENAI_API_KEY" not in prompt

