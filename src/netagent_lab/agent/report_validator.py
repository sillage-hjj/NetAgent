from __future__ import annotations

from typing import Iterable

from netagent_lab.agent.schemas import AgentReport, validate_agent_report
from netagent_lab.normalization.schemas import EvidenceRef


EXECUTED_REMEDIATION_PHRASES = (
    "fixed",
    "restarted",
    "changed acl",
    "shut interface",
    "shutdown interface",
    "cleared bgp",
    "applied",
    "executed remediation",
)


def validate_report_schema(report: dict) -> AgentReport:
    return validate_agent_report(report)


def validate_evidence_grounding(report: AgentReport, available_evidence: Iterable[EvidenceRef]) -> list[str]:
    available = {(ref.type, ref.id) for ref in available_evidence}
    errors: list[str] = []
    for finding in report.findings:
        for ref in finding.evidence:
            if (ref.type, ref.id) not in available:
                errors.append(f"Finding uses unknown evidence {ref.type}:{ref.id}")
    for hypothesis in report.root_cause_hypotheses:
        if hypothesis.likelihood in {"medium", "high"} and not hypothesis.evidence:
            errors.append("Medium/high root cause hypothesis lacks evidence")
        for ref in hypothesis.evidence:
            if (ref.type, ref.id) not in available:
                errors.append(f"Hypothesis uses unknown evidence {ref.type}:{ref.id}")
    for ref in report.evidence:
        if (ref.type, ref.id) not in available:
            errors.append(f"Report uses unknown evidence {ref.type}:{ref.id}")
    return errors


def validate_no_executed_remediation_claim(report: AgentReport) -> list[str]:
    errors: list[str] = []
    text_fields = [report.summary]
    text_fields.extend(finding.claim for finding in report.findings)
    text_fields.extend(hypothesis.hypothesis for hypothesis in report.root_cause_hypotheses)
    text_fields.extend(suggestion.suggestion for suggestion in report.remediation_suggestions)
    for suggestion in report.remediation_suggestions:
        if not suggestion.requires_human_approval:
            errors.append("Remediation suggestions must require human approval")
    joined = "\n".join(text_fields).lower()
    for phrase in EXECUTED_REMEDIATION_PHRASES:
        if phrase in joined:
            errors.append(f"Report appears to claim executed remediation: {phrase}")
    return errors


def validate_report(report: dict, available_evidence: Iterable[EvidenceRef]) -> tuple[bool, list[str]]:
    try:
        parsed = validate_report_schema(report)
    except Exception as exc:
        return False, [str(exc)]
    errors = validate_evidence_grounding(parsed, available_evidence)
    errors.extend(validate_no_executed_remediation_claim(parsed))
    return not errors, errors

