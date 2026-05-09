from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.guardrails import classify_action
from netagent_lab.metrics import find_anomalous_metrics_on_path
from netagent_lab.tools import (
    check_acl_tool,
    find_relevant_events_on_path,
    get_recent_events,
    get_ticket,
    infer_path_tool,
)


SITE_TO_DEVICE = {"Zurich": "client_zurich"}
SERVICE_TO_DEVICE = {"App-B": "app_b"}
SITE_TO_SOURCE_IP = {"Zurich": "10.1.0.25"}
SERVICE_TO_IP = {"App-B": "10.2.0.10"}


def investigate_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    tool_trace: list[dict[str, Any]] = []

    ticket_tool = get_ticket(conn, ticket_id)
    tool_trace.append(ticket_tool)
    if not ticket_tool["ok"]:
        return _result(
            ticket_id=ticket_id,
            summary=f"Ticket {ticket_id} could not be loaded.",
            root_cause_type="insufficient_evidence",
            root_cause="The ticket was not found, so no investigation facts are available.",
            confidence="low",
            impacted_path={"reachable": False, "path": []},
            evidence=[],
            tool_trace=tool_trace,
            recommended_next_checks=["Verify the ticket ID in the offline SQLite database."],
            remediation_suggestions=[],
        )

    ticket = ticket_tool["result"]
    mapping = _map_ticket(ticket)
    if mapping["errors"]:
        return _result(
            ticket_id=ticket_id,
            summary="The ticket could not be mapped to MVP source/destination entities.",
            root_cause_type="insufficient_evidence",
            root_cause="Structured ticket fields did not match the MVP offline mapping.",
            confidence="low",
            impacted_path={"reachable": False, "path": []},
            evidence=ticket_tool["evidence"],
            tool_trace=tool_trace,
            recommended_next_checks=mapping["errors"],
            remediation_suggestions=[],
        )

    path_tool = infer_path_tool(conn, mapping["src_device"], mapping["dst_device"])
    tool_trace.append(path_tool)
    events_tool = get_recent_events(conn)
    tool_trace.append(events_tool)

    path_result = path_tool["result"]
    evidence = _unique_evidence(ticket_tool["evidence"] + path_tool["evidence"])
    relevant_down_events = _filter_down_events(events_tool["result"])

    if not path_result["reachable"]:
        event_evidence = _event_evidence(relevant_down_events)
        evidence = _unique_evidence(evidence + event_evidence)
        if relevant_down_events:
            summary = (
                f"Ticket {ticket_id} maps Zurich to App-B over tcp/443. "
                f"Path inference found no reachable up-link path, and down link/routing events were present."
            )
            root_cause = (
                "The most likely cause is a down topology segment affecting the required path "
                f"from {mapping['src_device']} to {mapping['dst_device']}."
            )
            confidence = "high" if len(relevant_down_events) >= 2 else "medium"
            root_cause_type = "link_down"
        else:
            summary = "Path inference found no reachable up-link path, but no corroborating events were parsed."
            root_cause = "The path is unreachable in the offline topology, but RCA needs more event evidence."
            confidence = "low"
            root_cause_type = "insufficient_evidence"
        return _result(
            ticket_id=ticket_id,
            summary=summary,
            root_cause_type=root_cause_type,
            root_cause=root_cause,
            confidence=confidence,
            impacted_path=path_result,
            evidence=evidence,
            tool_trace=tool_trace,
            recommended_next_checks=[
                "Review parsed link_state_change and routing_neighbor_change events for affected interfaces.",
                "Verify the offline topology source for the down link status.",
            ],
            remediation_suggestions=[
                "Have a human network operator validate the physical/logical link before any repair action.",
            ],
        )

    acl_tool = check_acl_tool(
        conn,
        mapping["src_ip"],
        mapping["dst_ip"],
        mapping["protocol"],
        mapping["port"],
        path_result["path"],
    )
    tool_trace.append(acl_tool)
    evidence = _unique_evidence(evidence + acl_tool["evidence"])

    if acl_tool["result"]["result"] == "deny":
        acl_events = [event for event in events_tool["result"] if event["event_type"] == "acl_deny"]
        evidence = _unique_evidence(evidence + _event_evidence(acl_events))
        rule = acl_tool["result"]["matched_rule"]
        return _result(
            ticket_id=ticket_id,
            summary=(
                f"Ticket {ticket_id} maps to a reachable path, but tcp/443 is denied "
                f"by ACL rule {rule['rule_name']} on {rule['device']}."
            ),
            root_cause_type="acl_block",
            root_cause=f"ACL rule {rule['rule_name']} denies Zurich source traffic to App-B over tcp/443.",
            confidence="high",
            impacted_path=path_result,
            evidence=evidence,
            tool_trace=tool_trace,
            recommended_next_checks=[
                "Review the ACL rule intent and change history in an approved system of record.",
                "Compare parsed ACL deny events with affected source and destination IPs.",
            ],
            remediation_suggestions=[
                "Have a human owner review whether BLOCK_ZURICH should be changed through normal approval.",
            ],
        )

    metrics_result = find_anomalous_metrics_on_path(conn, path_result["path"])
    metrics_tool = {
        "tool_name": "find_anomalous_metrics_on_path",
        "ok": True,
        "result": metrics_result,
        "evidence": metrics_result["evidence"],
        "errors": [],
    }
    tool_trace.append(metrics_tool)
    evidence = _unique_evidence(evidence + metrics_result["evidence"])

    relevant_path_events = find_relevant_events_on_path(conn, path_result["path"])
    perf_events = [
        event
        for event in relevant_path_events["events"]
        if event["event_type"] in {"cpu_high", "packet_loss"}
    ]
    evidence = _unique_evidence(evidence + _event_evidence(perf_events))

    if metrics_result["anomalous"]:
        confidence = "high" if perf_events else "medium"
        return _result(
            ticket_id=ticket_id,
            summary=(
                f"Ticket {ticket_id} maps to a reachable path and ACL allows tcp/443, "
                "but path metrics show threshold violations."
            ),
            root_cause_type="performance_degradation",
            root_cause="Anomalous CPU or packet-loss metrics on an intermediate path device explain slow/unstable access.",
            confidence=confidence,
            impacted_path=path_result,
            evidence=evidence,
            tool_trace=tool_trace,
            recommended_next_checks=[
                "Review metric trend around the ticket timestamp for r2.",
                "Inspect parsed cpu_high and packet_loss events on path devices.",
            ],
            remediation_suggestions=[
                "Have a human operator assess capacity, process load, or congestion before taking action.",
            ],
        )

    return _result(
        ticket_id=ticket_id,
        summary="Path and ACL checks did not find a supported root cause, and metrics were normal.",
        root_cause_type="insufficient_evidence",
        root_cause="The offline evidence does not support a specific RCA.",
        confidence="low",
        impacted_path=path_result,
        evidence=evidence,
        tool_trace=tool_trace,
        recommended_next_checks=[
            "Add more synthetic telemetry or logs for this scenario.",
            "Check whether the ticket fields map to the expected MVP entities.",
        ],
        remediation_suggestions=[],
    )


def _map_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    src_site = ticket.get("src_site")
    dst_service = ticket.get("dst_service")
    protocol = ticket.get("protocol")
    port = ticket.get("port")
    errors: list[str] = []
    if src_site not in SITE_TO_DEVICE:
        errors.append(f"Unsupported source site for MVP mapping: {src_site}")
    if dst_service not in SERVICE_TO_DEVICE:
        errors.append(f"Unsupported destination service for MVP mapping: {dst_service}")
    if protocol != "tcp" or int(port or 0) != 443:
        errors.append("Only HTTPS as tcp/443 is mapped in the MVP.")

    return {
        "errors": errors,
        "src_device": SITE_TO_DEVICE.get(src_site),
        "dst_device": SERVICE_TO_DEVICE.get(dst_service),
        "src_ip": SITE_TO_SOURCE_IP.get(src_site),
        "dst_ip": SERVICE_TO_IP.get(dst_service),
        "protocol": "tcp",
        "port": 443,
    }


def _filter_down_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relevant: list[dict[str, Any]] = []
    for event in events:
        params = event["params"]
        if event["event_type"] == "link_state_change" and params.get("state") == "down":
            relevant.append(event)
        if event["event_type"] == "routing_neighbor_change" and params.get("to_state") == "DOWN":
            relevant.append(event)
    return relevant


def _event_evidence(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "type": "event",
            "id": event["id"],
            "description": (
                f"{event['event_type']} on {event['device']} at {event['ts']} "
                f"from raw log {event['raw_log_id']}."
            ),
        }
        for event in events
    ]


def _unique_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("type")), str(item.get("id")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _result(
    *,
    ticket_id: str,
    summary: str,
    root_cause_type: str,
    root_cause: str,
    confidence: str,
    impacted_path: dict[str, Any],
    evidence: list[dict[str, Any]],
    tool_trace: list[dict[str, Any]],
    recommended_next_checks: list[str],
    remediation_suggestions: list[str],
) -> dict[str, Any]:
    return {
        "ticket_id": ticket_id,
        "summary": _append_evidence_hint(summary, evidence),
        "root_cause_type": root_cause_type,
        "root_cause": _append_evidence_hint(root_cause, evidence),
        "confidence": confidence,
        "impacted_path": impacted_path,
        "evidence": evidence,
        "tool_trace": tool_trace,
        "recommended_next_checks": recommended_next_checks,
        "human_approved_remediation_suggestions": remediation_suggestions,
        "guardrail_notes": [
            "This MVP is read-only and did not execute remediation.",
            classify_action("shutdown interface eth1")["reason"],
            classify_action("show interface status")["reason"],
        ],
    }


def _append_evidence_hint(text: str, evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return text
    priority = {"acl_rule": 1, "metric": 2, "event": 3, "path_result": 4, "ticket": 5, "link": 6}
    ordered = sorted(
        evidence,
        key=lambda item: (priority.get(str(item.get("type")), 99), str(item.get("id"))),
    )
    ids = ", ".join(str(item["id"]) for item in ordered[:5])
    return f"{text} Evidence: {ids}."
