from __future__ import annotations

from netagent_lab.evals.runner import run_all_agent_evals


def test_mock_agent_evals_pass() -> None:
    result = run_all_agent_evals("mock")
    assert result["passed"] is True
    assert len(result["results"]) >= 3

