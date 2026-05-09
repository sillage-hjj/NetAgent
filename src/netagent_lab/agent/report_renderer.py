from __future__ import annotations

from typing import Any

from netagent_lab.agent.schemas import AgentReport


def render_agent_report_json(report: AgentReport) -> dict[str, Any]:
    return report.model_dump(mode="json")


def render_agent_report_text(report: AgentReport) -> str:
    return render_agent_report_markdown(report).replace("# ", "").replace("## ", "")


def render_agent_report_markdown(report: AgentReport) -> str:
    lines = [
        f"# NetAgent Lab Agent Report",
        "",
        f"## Summary",
        report.summary,
        "",
        f"## Confidence",
        report.confidence,
        "",
        "## Findings",
    ]
    lines.extend(_bullets([f"{item.claim} [{', '.join(_evidence_ids(item.evidence))}]" for item in report.findings]))
    lines.append("")
    lines.append("## Root Cause Hypotheses")
    lines.extend(_bullets([f"{item.hypothesis} ({item.likelihood}) [{', '.join(_evidence_ids(item.evidence))}]" for item in report.root_cause_hypotheses]))
    lines.append("")
    lines.append("## Impacted Objects")
    lines.extend(_bullets([f"{item.object_type}:{item.object_id} - {item.impact} [{', '.join(_evidence_ids(item.evidence))}]" for item in report.impacted_objects]))
    lines.append("")
    lines.append("## Evidence")
    lines.extend(_bullets([f"{ref.type}:{ref.id} - {ref.description or ''}" for ref in report.evidence]))
    lines.append("")
    lines.append("## Recommended Next Read-Only Checks")
    lines.extend(_bullets([f"{item.check} ({item.tool_name or 'manual read-only'}) - {item.reason}" for item in report.recommended_next_checks]))
    lines.append("")
    lines.append("## Human-Approved Remediation Suggestions")
    lines.extend(_bullets([f"{item.suggestion} (requires approval: {item.requires_human_approval})" for item in report.remediation_suggestions]))
    lines.append("")
    lines.append("## Unsupported Claims")
    lines.extend(_bullets(report.unsupported_claims))
    lines.append("")
    lines.append("## Tool Trace")
    lines.extend(_bullets(report.tool_trace_ids))
    lines.append("")
    lines.append("## Guardrail Notes")
    lines.extend(_bullets(report.guardrail_notes))
    lines.append("")
    lines.append("## Model Usage")
    lines.append(str(report.model_usage or {}))
    return "\n".join(lines)


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _evidence_ids(refs) -> list[str]:
    return [f"{ref.type}:{ref.id}" for ref in refs]

