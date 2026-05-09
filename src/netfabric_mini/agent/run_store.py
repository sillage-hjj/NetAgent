from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from netfabric_mini.agent.session_store import ensure_agent_tables
from netfabric_mini.controls.redaction import redact_sensitive_fields
from netfabric_mini.llm.client_protocol import LLMToolCall


def create_run(
    conn: sqlite3.Connection,
    session_id: str,
    question: str,
    provider: str,
    model: str | None,
) -> str:
    ensure_agent_tables(conn)
    run_id = f"run-{uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO agent_runs
            (run_id, session_id, status, question, created_at, completed_at, provider, model,
             final_report_json, errors_json, usage_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, session_id, "running", question, _now(), None, provider, model, None, "[]", "{}"),
    )
    conn.commit()
    return run_id


def complete_run(conn: sqlite3.Connection, run_id: str, final_report: dict[str, Any], usage: dict[str, Any]) -> None:
    ensure_agent_tables(conn)
    conn.execute(
        """
        UPDATE agent_runs
        SET status = 'completed', completed_at = ?, final_report_json = ?, usage_json = ?
        WHERE run_id = ?
        """,
        (
            _now(),
            json.dumps(redact_sensitive_fields(final_report), sort_keys=True),
            json.dumps(redact_sensitive_fields(usage), sort_keys=True),
            run_id,
        ),
    )
    conn.commit()


def fail_run(conn: sqlite3.Connection, run_id: str, errors: list[str]) -> None:
    ensure_agent_tables(conn)
    conn.execute(
        "UPDATE agent_runs SET status = 'failed', completed_at = ?, errors_json = ? WHERE run_id = ?",
        (_now(), json.dumps(errors, sort_keys=True), run_id),
    )
    conn.commit()


def record_tool_call(
    conn: sqlite3.Connection,
    run_id: str,
    tool_call: LLMToolCall,
    result: Any,
    *,
    started_at: str | None = None,
) -> None:
    ensure_agent_tables(conn)
    started = started_at or _now()
    completed = _now()
    payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    conn.execute(
        """
        INSERT OR REPLACE INTO agent_tool_calls
            (trace_id, run_id, tool_call_id, tool_name, arguments_json, result_json,
             ok, started_at, completed_at, errors_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("trace_id", f"trace-{uuid4().hex[:12]}"),
            run_id,
            tool_call.id,
            tool_call.name,
            json.dumps(redact_sensitive_fields(tool_call.arguments), sort_keys=True),
            json.dumps(redact_sensitive_fields(payload), sort_keys=True),
            1 if payload.get("ok") else 0,
            started,
            completed,
            json.dumps(payload.get("errors", []), sort_keys=True),
        ),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    ensure_agent_tables(conn)
    row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
    return _decode_run(row) if row else None


def list_runs(conn: sqlite3.Connection, session_id: str | None = None) -> list[dict[str, Any]]:
    ensure_agent_tables(conn)
    if session_id:
        rows = conn.execute(
            "SELECT * FROM agent_runs WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM agent_runs ORDER BY created_at DESC").fetchall()
    return [_decode_run(row) for row in rows]


def list_tool_calls(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    ensure_agent_tables(conn)
    rows = conn.execute(
        "SELECT * FROM agent_tool_calls WHERE run_id = ? ORDER BY started_at",
        (run_id,),
    ).fetchall()
    calls = []
    for row in rows:
        item = dict(row)
        item["arguments"] = json.loads(item.pop("arguments_json"))
        item["result"] = json.loads(item.pop("result_json"))
        item["errors"] = json.loads(item.pop("errors_json"))
        calls.append(item)
    return calls


def _decode_run(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["final_report"] = json.loads(item.pop("final_report_json")) if item["final_report_json"] else None
    item["errors"] = json.loads(item.pop("errors_json"))
    item["usage"] = json.loads(item.pop("usage_json"))
    return item


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

