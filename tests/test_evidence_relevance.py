from __future__ import annotations

from netfabric_mini.agent.schemas import AgentReport
from netfabric_mini.evals.evidence_relevance import evaluate_evidence_relevance
from netfabric_mini.evals.expected_evidence import get_expected_evidence_spec
from netfabric_mini.evals.runner import run_all_agent_evals
from netfabric_mini.evals.scenarios import prepare_agent_scenario_db


def _report_with_evidence(evidence: list[dict]) -> AgentReport:
    return AgentReport(
        report_id="report-test",
        answer_type="network_investigation",
        user_question="test",
        summary="test summary",
        confidence="medium",
        findings=[{"claim": "test claim", "confidence": "medium", "evidence": evidence[:1]}],
        root_cause_hypotheses=[{"hypothesis": "test hypothesis", "likelihood": "medium", "evidence": evidence[:1]}],
        impacted_objects=[],
        recommended_next_checks=[],
        remediation_suggestions=[],
        evidence=evidence,
        unsupported_claims=[],
        tool_trace_ids=["trace-test"],
        guardrail_notes=["No remediation was executed."],
        data_budget={},
        model_usage={"provider": "mock"},
    )


def test_expected_evidence_specs_exist() -> None:
    assert get_expected_evidence_spec("link_failure").root_cause_type == "link_down"
    assert get_expected_evidence_spec("congestion").preferred_object_ids
    assert get_expected_evidence_spec("route_withdrawal").required_evidence_types


def test_unrelated_valid_evidence_fails_relevance() -> None:
    conn = prepare_agent_scenario_db("link_failure")
    report = _report_with_evidence([
        {"type": "service", "id": "app_b", "description": "Valid but generic service evidence."}
    ])

    result = evaluate_evidence_relevance(report, "link_failure", conn)

    assert result.passed is False
    assert result.missing_expected_evidence


def test_missing_expected_evidence_is_reported() -> None:
    conn = prepare_agent_scenario_db("congestion")
    report = _report_with_evidence([
        {"type": "link", "id": "link_r1_r2", "description": "Only link evidence."}
    ])

    result = evaluate_evidence_relevance(report, "congestion", conn)

    assert "probe" in result.missing_expected_evidence
    assert result.passed is False


def test_mock_evals_pass_relevance_for_core_scenarios() -> None:
    result = run_all_agent_evals("mock")

    assert result["passed"] is True
    for item in result["results"]:
        if item["scenario"] in {"link_failure", "congestion", "route_withdrawal"}:
            relevance = item["score"]["evidence_relevance"]
            assert relevance["passed"] is True
            assert relevance["overall_grounding_score"] >= 0.70

