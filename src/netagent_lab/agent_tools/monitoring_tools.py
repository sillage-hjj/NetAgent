from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.agent_tools._common import ok_result
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.orchestration.monitoring_workflow import run_monitoring_cycle as _run_monitoring_cycle
from netagent_lab.reasoning.alerts import evaluate_alerts


def run_monitoring_cycle(conn: sqlite3.Connection, args: dict[str, Any]):
    result = _run_monitoring_cycle(conn, args.get("focus"))
    payload = result.model_dump(mode="json")
    return ok_result("run_monitoring_cycle", payload, fallback_evidence=[{"type": "snapshot", "id": payload["snapshot_id"]}], data_budget=payload.get("export_refs"))


def get_active_alerts(conn: sqlite3.Connection, args: dict[str, Any]):
    alerts = evaluate_alerts(KnowledgeBase.from_db(conn))
    severity = args.get("severity")
    if severity:
        alerts = [alert for alert in alerts if alert.get("severity") == severity]
    return ok_result("get_active_alerts", {"alerts": alerts})

