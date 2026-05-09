from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from netfabric_mini.agent.session_store import ensure_agent_tables
from netfabric_mini.controls.redaction import redact_sensitive_fields


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    run_id: str
    requested_by: str = "agent"
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: str
    decided_at: str | None = None


def create_approval_request(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    requested_by: str = "agent",
) -> Approval:
    ensure_agent_tables(conn)
    approval = Approval(
        approval_id=f"approval-{uuid4().hex[:12]}",
        run_id=run_id,
        requested_by=requested_by,
        tool_name=tool_name,
        arguments=redact_sensitive_fields(arguments),
        created_at=_now(),
    )
    conn.execute(
        """
        INSERT INTO agent_approvals
            (approval_id, run_id, tool_name, arguments_json, status, created_at, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            approval.approval_id,
            approval.run_id,
            approval.tool_name,
            json.dumps(approval.arguments, sort_keys=True),
            approval.status,
            approval.created_at,
            approval.decided_at,
        ),
    )
    conn.commit()
    return approval


def approve_request(conn: sqlite3.Connection, approval_id: str) -> Approval:
    return _decide(conn, approval_id, "approved")


def reject_request(conn: sqlite3.Connection, approval_id: str) -> Approval:
    return _decide(conn, approval_id, "rejected")


def get_approval(conn: sqlite3.Connection, approval_id: str) -> Approval | None:
    ensure_agent_tables(conn)
    row = conn.execute("SELECT * FROM agent_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    return _row_to_approval(row) if row else None


def list_pending_approvals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_agent_tables(conn)
    rows = conn.execute(
        "SELECT * FROM agent_approvals WHERE status = 'pending' ORDER BY created_at"
    ).fetchall()
    return [_row_to_approval(row).model_dump(mode="json") for row in rows]


def _decide(conn: sqlite3.Connection, approval_id: str, status: Literal["approved", "rejected"]) -> Approval:
    ensure_agent_tables(conn)
    decided_at = _now()
    conn.execute(
        "UPDATE agent_approvals SET status = ?, decided_at = ? WHERE approval_id = ?",
        (status, decided_at, approval_id),
    )
    conn.commit()
    approval = get_approval(conn, approval_id)
    if approval is None:
        raise KeyError(f"Unknown approval: {approval_id}")
    return approval


def _row_to_approval(row: dict[str, Any]) -> Approval:
    return Approval(
        approval_id=row["approval_id"],
        run_id=row["run_id"],
        tool_name=row["tool_name"],
        arguments=json.loads(row["arguments_json"]),
        status=row["status"],
        created_at=row["created_at"],
        decided_at=row["decided_at"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

