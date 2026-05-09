from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from netfabric_mini.controls.redaction import redact_sensitive_fields


def ensure_agent_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            title TEXT,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            run_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            status TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            provider TEXT NOT NULL,
            model TEXT,
            final_report_json TEXT,
            errors_json TEXT NOT NULL,
            usage_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_tool_calls (
            trace_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            tool_call_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            ok INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            errors_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_approvals (
            approval_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            decided_at TEXT
        );
        """
    )
    conn.commit()


def create_session(conn: sqlite3.Connection, title: str | None = None, metadata: dict[str, Any] | None = None) -> str:
    ensure_agent_tables(conn)
    now = _now()
    session_id = f"session-{uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO agent_sessions (session_id, created_at, updated_at, title, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, now, now, title, json.dumps(redact_sensitive_fields(metadata or {}), sort_keys=True)),
    )
    conn.commit()
    return session_id


def append_message(
    conn: sqlite3.Connection,
    session_id: str,
    role: str,
    content: str,
    run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_agent_tables(conn)
    message_id = f"message-{uuid4().hex[:12]}"
    now = _now()
    conn.execute(
        """
        INSERT INTO agent_messages
            (message_id, session_id, run_id, role, content, created_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message_id,
            session_id,
            run_id,
            role,
            content,
            now,
            json.dumps(redact_sensitive_fields(metadata or {}), sort_keys=True),
        ),
    )
    conn.execute("UPDATE agent_sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
    conn.commit()
    return message_id


def get_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    ensure_agent_tables(conn)
    row = conn.execute("SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json"))
    return item


def list_messages(conn: sqlite3.Connection, session_id: str) -> list[dict[str, Any]]:
    ensure_agent_tables(conn)
    rows = conn.execute(
        "SELECT * FROM agent_messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    ).fetchall()
    messages = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        messages.append(item)
    return messages


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

