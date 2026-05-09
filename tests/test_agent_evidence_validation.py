import pytest

from netfabric_mini.agent.schemas import validate_agent_report


def test_valid_report_schema_passes() -> None:
    report = _report()

    assert validate_agent_report(report).report_id == "r1"


def test_finding_without_evidence_fails() -> None:
    report = _report()
    report["findings"][0]["evidence"] = []

    with pytest.raises(ValueError):
        validate_agent_report(report)


def test_remediation_claiming_execution_fails() -> None:
    report = _report()
    report["remediation_suggestions"][0]["suggestion"] = "Restarted r2 and fixed it"

    with pytest.raises(ValueError):
        validate_agent_report(report)


def _report():
    evidence = [{"type": "event", "id": "event-1", "description": "e"}]
    return {
        "report_id": "r1",
        "answer_type": "network_investigation",
        "user_question": "why",
        "summary": "supported",
        "confidence": "high",
        "findings": [{"claim": "supported", "confidence": "high", "evidence": evidence}],
        "root_cause_hypotheses": [{"hypothesis": "supported", "likelihood": "high", "evidence": evidence}],
        "impacted_objects": [{"object_type": "link", "object_id": "l1", "impact": "down", "evidence": evidence}],
        "recommended_next_checks": [{"check": "check", "tool_name": "x", "reason": "r", "read_only": True}],
        "remediation_suggestions": [{"suggestion": "Human may review a simulated change.", "requires_human_approval": True, "destructive": False, "evidence": evidence}],
        "evidence": evidence,
        "unsupported_claims": [],
        "tool_trace_ids": ["trace-1"],
        "guardrail_notes": ["No remediation was executed."],
        "data_budget": {},
        "model_usage": {"provider": "mock"},
    }

