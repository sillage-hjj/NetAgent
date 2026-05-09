from __future__ import annotations

import json
import sqlite3
from typing import Any

from netagent_lab.agent.prompts import build_repair_prompt, build_system_prompt, build_user_prompt
from netagent_lab.agent.report_validator import validate_report
from netagent_lab.agent.run_store import complete_run, create_run, fail_run, record_tool_call
from netagent_lab.agent.schemas import AgentReport, validate_agent_report
from netagent_lab.agent.session_store import append_message, create_session, get_session
from netagent_lab.agent.tool_executor import ToolExecutor
from netagent_lab.agent.tool_registry import ToolRegistry
from netagent_lab.controls.evidence import collect_evidence_refs
from netagent_lab.llm.client_protocol import LLMClientProtocol, LLMMessage
from netagent_lab.llm.config import LLMProviderConfig
from netagent_lab.normalization.schemas import EvidenceRef
from netagent_lab.orchestration.investigation_context import build_investigation_context


class NetworkAgent:
    def __init__(
        self,
        *,
        db: sqlite3.Connection,
        llm_client: LLMClientProtocol,
        tool_registry: ToolRegistry,
        config: LLMProviderConfig,
    ) -> None:
        self.db = db
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.config = config
        self.executor = ToolExecutor(tool_registry)

    def run(self, question: str, session_id: str | None = None, focus: dict[str, Any] | None = None) -> AgentReport:
        if session_id is None or get_session(self.db, session_id) is None:
            session_id = create_session(self.db, title=question[:80])
        run_id = create_run(self.db, session_id, question, self.config.provider, self.config.model)
        append_message(self.db, session_id, "user", question, run_id)

        context = build_investigation_context(
            self.db,
            focus,
            {
                "max_events": self.config.max_context_events,
                "max_telemetry_samples": self.config.max_context_telemetry,
            },
        )
        available_evidence = _available_context_evidence(context)
        messages = [
            LLMMessage(role="system", content=build_system_prompt(self.config)),
            LLMMessage(role="user", content=build_user_prompt(question, _compact_context(context))),
        ]
        tool_specs = self.tool_registry.to_llm_tool_specs()
        tool_trace_ids: list[str] = []
        usage: dict[str, Any] = {}
        previous_response_id: str | None = None
        repair_attempted = False
        tool_call_count = 0

        try:
            while True:
                response = self.llm_client.create_response(
                    messages=messages,
                    tools=tool_specs,
                    response_schema=AgentReport.model_json_schema(),
                    previous_response_id=previous_response_id,
                    max_output_tokens=self.config.max_output_tokens,
                )
                previous_response_id = response.id
                usage = _merge_usage(usage, response.usage)
                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_call_count += 1
                        if tool_call_count > self.config.max_tool_calls:
                            report = _safe_error_report(question, "Tool call limit exceeded", available_evidence, tool_trace_ids, usage, context)
                            complete_run(self.db, run_id, report.model_dump(mode="json"), usage)
                            return report
                        result = self.executor.execute(tool_call)
                        tool_trace_ids.append(result.trace_id)
                        available_evidence.extend(result.evidence)
                        record_tool_call(self.db, run_id, tool_call, result)
                        messages.append(
                            LLMMessage(
                                role="tool",
                                tool_call_id=tool_call.id,
                                content=json.dumps(result.model_dump(mode="json"), sort_keys=True),
                            )
                        )
                    continue

                candidate = response.structured_output or _json_content(response.content)
                if candidate is None:
                    candidate = _safe_error_report(question, "LLM returned no structured report", available_evidence, tool_trace_ids, usage, context).model_dump(mode="json")
                if not candidate.get("user_question"):
                    candidate["user_question"] = question
                candidate["tool_trace_ids"] = tool_trace_ids
                candidate.setdefault("guardrail_notes", [])
                candidate["guardrail_notes"] = list(
                    dict.fromkeys(candidate["guardrail_notes"] + ["Read-only tools were enforced; no remediation was executed."])
                )
                candidate.setdefault("data_budget", context.get("budget", {}))
                candidate["model_usage"] = usage
                is_valid, errors = validate_report(candidate, _dedupe_evidence(available_evidence))
                if is_valid:
                    report = validate_agent_report(candidate)
                    complete_run(self.db, run_id, report.model_dump(mode="json"), usage)
                    return report
                if not repair_attempted:
                    repair_attempted = True
                    messages.append(LLMMessage(role="assistant", content=json.dumps(candidate, sort_keys=True)))
                    messages.append(LLMMessage(role="user", content=build_repair_prompt(errors, candidate)))
                    continue
                report = _safe_error_report(question, "; ".join(errors), available_evidence, tool_trace_ids, usage, context)
                complete_run(self.db, run_id, report.model_dump(mode="json"), usage)
                return report
        except Exception as exc:
            fail_run(self.db, run_id, [str(exc)])
            return _safe_error_report(question, str(exc), available_evidence, tool_trace_ids, usage, context)


def _available_context_evidence(context: dict[str, Any]) -> list[EvidenceRef]:
    refs = [EvidenceRef(type="context", id="initial-context", description="Budgeted initial investigation context.")]
    refs.extend(collect_evidence_refs(context))
    return _dedupe_evidence(refs)


def _dedupe_evidence(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[tuple[str, str]] = set()
    result: list[EvidenceRef] = []
    for ref in refs:
        key = (ref.type, ref.id)
        if key not in seen:
            seen.add(key)
            result.append(ref)
    return result


def _compact_context(context: dict[str, Any]) -> str:
    summary = {
        "topology_summary": context.get("topology_summary"),
        "current_tick": context.get("current_tick"),
        "active_alerts": context.get("active_alerts", [])[:5],
        "latest_snapshot_id": context.get("latest_snapshot_id"),
        "evidence_ids": context.get("evidence_ids", [])[:20],
        "budget": context.get("budget"),
    }
    return json.dumps(summary, sort_keys=True)


def _json_content(content: str | None) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _merge_usage(current: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in (new or {}).items():
        if isinstance(value, (int, float)) and isinstance(merged.get(key), (int, float)):
            merged[key] += value
        else:
            merged[key] = value
    return merged


def _safe_error_report(
    question: str,
    error: str,
    available_evidence: list[EvidenceRef],
    tool_trace_ids: list[str],
    usage: dict[str, Any],
    context: dict[str, Any],
) -> AgentReport:
    evidence = available_evidence[:1] or [EvidenceRef(type="context", id="initial-context", description="Initial context.")]
    return AgentReport(
        report_id="agent-report-error",
        answer_type="tool_error_report",
        user_question=question,
        summary=f"Agent could not complete the investigation safely: {error}",
        confidence="low",
        findings=[
            {
                "claim": "The investigation result is incomplete and should be treated as insufficient evidence.",
                "confidence": "low",
                "evidence": evidence,
            }
        ],
        root_cause_hypotheses=[],
        impacted_objects=[],
        recommended_next_checks=[
            {
                "check": "Run a monitoring cycle and inspect alerts.",
                "tool_name": "run_monitoring_cycle",
                "reason": "Collect fresh deterministic evidence.",
                "read_only": True,
            }
        ],
        remediation_suggestions=[],
        evidence=evidence,
        unsupported_claims=[error],
        tool_trace_ids=tool_trace_ids,
        guardrail_notes=["No remediation was executed.", "Only registered tools may access network facts."],
        data_budget=context.get("budget", {}),
        model_usage=usage,
    )
