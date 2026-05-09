from __future__ import annotations

import json
from collections import deque
from typing import Any

from netfabric_mini.llm.client_protocol import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec


class MockLLMClient:
    def __init__(self, script_name: str | None = None, responses: list[LLMResponse] | None = None):
        self.script_name = script_name
        self._scripted_mode = responses is None
        self.responses = deque(responses or _scripted_responses(script_name))
        self.calls: list[dict[str, Any]] = []

    def create_response(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        response_schema: dict[str, Any] | None,
        previous_response_id: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": [message.model_dump(mode="json") for message in messages],
                "tools": [tool.name for tool in tools],
                "previous_response_id": previous_response_id,
                "max_output_tokens": max_output_tokens,
            }
        )
        if self.responses:
            response = self.responses.popleft()
            if self._scripted_mode and not response.tool_calls and response.structured_output is not None:
                return LLMResponse(
                    id=response.id,
                    content=response.content,
                    tool_calls=[],
                    structured_output=_report_from_tool_messages(messages, self.script_name),
                    usage=response.usage,
                )
            return response
        return LLMResponse(
            id="mock-final",
            content=None,
            structured_output=_report_from_tool_messages(messages, self.script_name),
            tool_calls=[],
            usage={"provider": "mock", "responses": len(self.calls)},
        )


def _scripted_responses(script_name: str | None) -> list[LLMResponse]:
    if script_name in {"link_failure", "route_withdrawal", "service_unreachable"}:
        return [
            LLMResponse(
                id="mock-1",
                tool_calls=[
                    LLMToolCall(id="tc-1", name="run_monitoring_cycle", arguments={}),
                    LLMToolCall(id="tc-2", name="get_active_alerts", arguments={}),
                    LLMToolCall(
                        id="tc-3",
                        name="check_service_reachability",
                        arguments={"source_device": "client_zurich", "service_id": "app_b"},
                    ),
                    LLMToolCall(
                        id="tc-4",
                        name="infer_path",
                        arguments={"src_device": "client_zurich", "dst_device": "app_b"},
                    ),
                    LLMToolCall(id="tc-5", name="get_recent_events", arguments={}),
                ],
                usage={"provider": "mock"},
            ),
            LLMResponse(
                id="mock-2",
                structured_output=_default_report("App-B reachability investigation completed."),
                usage={"provider": "mock"},
            ),
        ]
    if script_name == "congestion":
        return [
            LLMResponse(
                id="mock-1",
                tool_calls=[
                    LLMToolCall(id="tc-1", name="get_current_context", arguments={}),
                    LLMToolCall(id="tc-2", name="collect_link_states", arguments={}),
                    LLMToolCall(id="tc-3", name="evaluate_alerts", arguments={}),
                ],
                usage={"provider": "mock"},
            ),
            LLMResponse(
                id="mock-2",
                structured_output=_default_report("Congestion investigation completed."),
                usage={"provider": "mock"},
            ),
        ]
    return [
        LLMResponse(
            id="mock-1",
            tool_calls=[LLMToolCall(id="tc-1", name="get_current_context", arguments={})],
            usage={"provider": "mock"},
        ),
        LLMResponse(
            id="mock-2",
            structured_output=_default_report("Network state investigation completed."),
            usage={"provider": "mock"},
        ),
    ]


def _default_report(summary: str) -> dict[str, Any]:
    evidence = [{"type": "context", "id": "initial-context", "description": "Budgeted investigation context."}]
    return {
        "report_id": "agent-report-mock",
        "answer_type": "network_investigation",
        "user_question": "",
        "summary": summary,
        "confidence": "medium",
        "findings": [{"claim": summary, "confidence": "medium", "evidence": evidence}],
        "root_cause_hypotheses": [{"hypothesis": "See deterministic tool evidence.", "likelihood": "medium", "evidence": evidence}],
        "impacted_objects": [],
        "recommended_next_checks": [{"check": "Review deterministic tool output.", "tool_name": "get_current_context", "reason": "Confirm evidence.", "read_only": True}],
        "remediation_suggestions": [{"suggestion": "Have a human review any simulated mutation before approval.", "requires_human_approval": True, "destructive": False, "evidence": evidence}],
        "evidence": evidence,
        "unsupported_claims": [],
        "tool_trace_ids": [],
        "guardrail_notes": ["No remediation was executed.", "Mock provider used."],
        "data_budget": {},
        "model_usage": {"provider": "mock"},
    }


def _report_from_tool_messages(messages: list[LLMMessage], script_name: str | None) -> dict[str, Any]:
    payloads = []
    for message in messages:
        if message.role != "tool":
            continue
        try:
            payloads.append(json.loads(message.content))
        except json.JSONDecodeError:
            continue
    refs = _collect_refs(payloads)
    if not refs:
        refs = [{"type": "context", "id": "initial-context", "description": "Budgeted investigation context."}]

    alerts = []
    events = []
    reachability = {}
    links = {}
    for payload in payloads:
        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            continue
        alerts.extend(result.get("alerts") or [])
        events.extend(result.get("events") or [])
        if "reachable" in result:
            reachability = result
        if isinstance(result.get("links"), dict):
            links.update(result["links"])

    alert_types = {alert.get("alert_type") for alert in alerts}
    event_types = {event.get("event_type") for event in events}
    if "route_withdrawal" in event_types or script_name == "route_withdrawal":
        summary = "App-B reachability is blocked by a simulated route withdrawal evidenced by deterministic event and reachability data."
        hypothesis = "A route withdrawal between client_zurich and app_b is the most likely cause."
        impacted = [{"object_type": "service", "object_id": "app_b", "impact": "unreachable from client_zurich", "evidence": refs[:2]}]
    elif {"high_utilization", "high_packet_loss", "high_latency"} & alert_types or script_name == "congestion":
        summary = "The path to App-B is reachable but degraded by congestion indicators such as high utilization, packet loss, or latency."
        hypothesis = "Congestion on an intermediate link is the most likely degradation source."
        impacted = _impacted_from_alerts(alerts, refs)
    elif "link_down" in alert_types or script_name == "link_failure":
        summary = "A simulated link failure is present; deterministic pathing and alerts should be used to confirm whether backup reachability remains."
        hypothesis = "A down link on the branch-to-app topology is the most likely incident trigger."
        impacted = _impacted_from_alerts(alerts, refs)
    elif reachability and not reachability.get("reachable", True):
        summary = "Service reachability is currently unavailable according to deterministic reachability tools."
        hypothesis = "The service is unreachable, but more evidence is needed to isolate the root cause."
        impacted = [{"object_type": "service", "object_id": reachability.get("target_service", "unknown"), "impact": "unreachable", "evidence": refs[:2]}]
    else:
        summary = "The agent reviewed deterministic context and did not find a supported critical outage."
        hypothesis = "No high-confidence root cause is supported by the available evidence."
        impacted = []

    return {
        "report_id": "agent-report-mock",
        "answer_type": "network_investigation",
        "user_question": "",
        "summary": summary,
        "confidence": "medium",
        "findings": [{"claim": summary, "confidence": "medium", "evidence": refs[:3]}],
        "root_cause_hypotheses": [{"hypothesis": hypothesis, "likelihood": "medium", "evidence": refs[:3]}],
        "impacted_objects": impacted,
        "recommended_next_checks": [
            {"check": "Inspect active alerts and reachability evidence.", "tool_name": "evaluate_alerts", "reason": "Confirm deterministic state before any action.", "read_only": True}
        ],
        "remediation_suggestions": [
            {"suggestion": "Have a human approve any simulated recovery event before applying it.", "requires_human_approval": True, "destructive": False, "evidence": refs[:1]}
        ],
        "evidence": refs[:10],
        "unsupported_claims": [],
        "tool_trace_ids": [],
        "guardrail_notes": ["No remediation was executed.", "Mock provider used."],
        "data_budget": {},
        "model_usage": {"provider": "mock"},
    }


def _collect_refs(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            evidence = value.get("evidence")
            if isinstance(evidence, list):
                for ref in evidence:
                    if isinstance(ref, dict) and {"type", "id"} <= set(ref) and isinstance(ref.get("type"), str):
                        refs.append({"type": ref["type"], "id": ref["id"], "description": ref.get("description")})
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payloads)
    seen = set()
    unique = []
    for ref in refs:
        key = (ref["type"], ref["id"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    priority = {"event": 0, "link": 1, "probe": 2, "service": 3, "telemetry": 4, "device": 5, "topology": 6}
    return sorted(unique, key=lambda ref: (priority.get(ref["type"], 99), ref["id"]))


def _impacted_from_alerts(alerts: list[dict[str, Any]], refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    impacted = []
    for alert in alerts[:3]:
        impacted.append(
            {
                "object_type": alert.get("target_type", "object"),
                "object_id": alert.get("target_id", "unknown"),
                "impact": alert.get("summary", "alerted"),
                "evidence": alert.get("evidence") or refs[:1],
            }
        )
    return impacted
