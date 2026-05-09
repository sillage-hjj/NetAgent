from __future__ import annotations

from typing import Any


def render_markdown_report(result: dict[str, Any]) -> str:
    path = _format_path(result.get("impacted_path", {}))
    lines = [
        f"# Network Incident Report: {result['ticket_id']}",
        "",
        "## Summary",
        result["summary"],
        "",
        "## Most likely root cause",
        f"{result['root_cause_type']}: {result['root_cause']}",
        "",
        "## Confidence",
        result["confidence"],
        "",
        "## Impacted path",
        path,
        "",
        "## Evidence",
        *_format_evidence(result.get("evidence", [])),
        "",
        "## Tool trace",
        *_format_tool_trace(result.get("tool_trace", [])),
        "",
        "## Recommended next read-only checks",
        *_format_list(result.get("recommended_next_checks", [])),
        "",
        "## Human-approved remediation suggestions",
        "Remediation was not executed by this MVP.",
        *_format_list(result.get("human_approved_remediation_suggestions", [])),
        "",
        "## Guardrail notes",
        "Evidence is based on offline synthetic data.",
        *_format_list(result.get("guardrail_notes", [])),
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_text_report(result: dict[str, Any]) -> str:
    markdown = render_markdown_report(result)
    text = markdown.replace("# ", "").replace("## ", "")
    return text


def _format_path(path_result: dict[str, Any]) -> str:
    if not path_result:
        return "No path result available."
    if path_result.get("reachable"):
        return " -> ".join(path_result.get("path", []))
    src = path_result.get("src_device", "unknown-src")
    dst = path_result.get("dst_device", "unknown-dst")
    return f"{src} -> {dst} is unreachable using up links only."


def _format_evidence(evidence: list[dict[str, Any]]) -> list[str]:
    if not evidence:
        return ["- No evidence items were available."]
    return [f"- [{item['type']}] {item['id']}: {item['description']}" for item in evidence]


def _format_tool_trace(tool_trace: list[dict[str, Any]]) -> list[str]:
    if not tool_trace:
        return ["- No tool calls were recorded."]
    return [
        f"- {entry['tool_name']}: {'ok' if entry.get('ok') else 'error'}"
        for entry in tool_trace
    ]


def _format_list(items: list[str]) -> list[str]:
    if not items:
        return ["- None."]
    return [f"- {item}" for item in items]

