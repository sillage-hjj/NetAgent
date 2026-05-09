from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from netfabric_mini.normalization.schemas import EvidenceRef


Confidence = Literal["low", "medium", "high"]


class AgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class AgentFinding(AgentModel):
    claim: str
    confidence: Confidence
    evidence: list[EvidenceRef] = Field(min_length=1)


class RootCauseHypothesis(AgentModel):
    hypothesis: str
    likelihood: Confidence
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_evidence_for_supported_hypotheses(self) -> "RootCauseHypothesis":
        if self.likelihood in {"medium", "high"} and not self.evidence:
            raise ValueError("Medium/high root cause hypotheses require evidence")
        return self


class ImpactedObject(AgentModel):
    object_type: str
    object_id: str
    impact: str
    evidence: list[EvidenceRef] = Field(min_length=1)


class RecommendedCheck(AgentModel):
    check: str
    tool_name: str | None = None
    reason: str
    read_only: bool = True


class RemediationSuggestion(AgentModel):
    suggestion: str
    requires_human_approval: bool = True
    destructive: bool = False
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @field_validator("suggestion")
    @classmethod
    def reject_executed_language(cls, value: str) -> str:
        lowered = value.lower()
        forbidden = ("executed", "restarted", "changed acl", "shut interface", "fixed", "applied")
        if any(word in lowered for word in forbidden):
            raise ValueError("Remediation suggestions must not claim execution")
        return value


class AgentReport(AgentModel):
    report_id: str
    answer_type: Literal[
        "network_investigation",
        "monitoring_summary",
        "state_explanation",
        "insufficient_evidence",
        "tool_error_report",
    ]
    user_question: str
    summary: str
    confidence: Confidence
    findings: list[AgentFinding]
    root_cause_hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    impacted_objects: list[ImpactedObject] = Field(default_factory=list)
    recommended_next_checks: list[RecommendedCheck] = Field(default_factory=list)
    remediation_suggestions: list[RemediationSuggestion] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    tool_trace_ids: list[str] = Field(default_factory=list)
    guardrail_notes: list[str] = Field(default_factory=list)
    data_budget: dict = Field(default_factory=dict)
    model_usage: dict | None = None

    @model_validator(mode="after")
    def require_report_evidence(self) -> "AgentReport":
        if self.answer_type != "insufficient_evidence" and not self.evidence:
            raise ValueError("Agent reports require evidence")
        return self


def validate_agent_report(report: dict) -> AgentReport:
    return AgentReport.model_validate(report)
