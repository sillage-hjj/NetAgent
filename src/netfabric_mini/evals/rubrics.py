from __future__ import annotations

import sqlite3

from netfabric_mini.agent.schemas import AgentReport
from netfabric_mini.evals.evidence_relevance import evaluate_evidence_relevance


def score_report(
    report: AgentReport,
    scenario_name: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, object]:
    summary = report.summary.lower()
    checks = {
        "structured_report_valid": True,
        "evidence_present": bool(report.evidence),
        "no_executed_remediation": "executed remediation" not in summary and "restarted" not in summary,
        "tool_usage_present": bool(report.tool_trace_ids),
        "next_checks_present": bool(report.recommended_next_checks),
    }
    if scenario_name == "link_failure":
        checks["correct_category_hint"] = "link" in summary or "reachability" in summary
    elif scenario_name == "congestion":
        checks["correct_category_hint"] = any(word in summary for word in ("congestion", "loss", "latency", "utilization", "degraded"))
    elif scenario_name == "route_withdrawal":
        checks["correct_category_hint"] = "route" in summary or "withdrawal" in summary
    else:
        checks["correct_category_hint"] = True
    relevance = evaluate_evidence_relevance(report, scenario_name, conn)
    checks["evidence_relevance_passed"] = relevance.passed
    return {
        "passed": all(bool(value) for value in checks.values()),
        "checks": checks,
        "evidence_relevance": relevance.model_dump(mode="json"),
    }
