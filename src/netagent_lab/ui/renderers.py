from __future__ import annotations

import json
from typing import Any


def to_pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def summarize_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("result")
    return {
        "ok": result.get("ok"),
        "tool_name": result.get("tool_name"),
        "evidence_count": len(result.get("evidence", [])),
        "errors": result.get("errors", []),
        "result_type": type(payload).__name__,
    }


def evidence_table_rows(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": ref.get("type"),
            "id": ref.get("id"),
            "description": ref.get("description"),
        }
        for ref in refs
    ]


def diff_summary_rows(diff: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not diff:
        return []
    keys = ["changed_links", "changed_services", "changed_probes", "new_alerts", "resolved_alerts", "new_events"]
    return [{"category": key, "count": len(diff.get(key, []))} for key in keys]

