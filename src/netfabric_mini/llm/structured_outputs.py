from __future__ import annotations

from netfabric_mini.agent.schemas import AgentReport, validate_agent_report


def agent_report_json_schema() -> dict:
    return AgentReport.model_json_schema()


__all__ = ["agent_report_json_schema", "validate_agent_report", "AgentReport"]

