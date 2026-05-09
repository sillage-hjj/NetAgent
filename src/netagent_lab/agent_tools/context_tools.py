from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.agent_tools._common import ok_result
from netagent_lab.orchestration.investigation_context import build_investigation_context


def get_current_context(conn: sqlite3.Connection, args: dict[str, Any]):
    payload = build_investigation_context(conn, args.get("focus"), args.get("budget"))
    return ok_result("get_current_context", payload, fallback_evidence=[{"type": "context", "id": "initial-context"}], data_budget=payload.get("budget"))


def export_llm_context(conn: sqlite3.Connection, args: dict[str, Any]):
    payload = build_investigation_context(conn, args.get("focus"), args.get("budget"))
    return ok_result("export_llm_context", payload, fallback_evidence=[{"type": "context", "id": "llm-context"}], data_budget=payload.get("budget"))

