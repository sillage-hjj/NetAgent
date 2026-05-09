from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.agent.approvals import create_approval_request, get_approval
from netfabric_mini.agent_tools._common import ok_result
from netfabric_mini.sim.engine import SimulationEngine


def propose_sim_event(conn: sqlite3.Connection, args: dict[str, Any], *, run_id: str = "run-unknown"):
    approval = create_approval_request(
        conn,
        run_id=run_id,
        tool_name="apply_approved_sim_event",
        arguments=args,
    )
    payload = {
        "proposal": args,
        "approval_id": approval.approval_id,
        "status": approval.status,
        "requires_human_approval": True,
        "note": "No simulated state was mutated.",
        "evidence": [{"type": "approval", "id": approval.approval_id, "description": "Pending simulated mutation approval."}],
    }
    return ok_result("propose_sim_event", payload, read_only=True)


def apply_approved_sim_event(conn: sqlite3.Connection, args: dict[str, Any]):
    approval = get_approval(conn, args["approval_id"])
    if approval is None:
        raise ValueError("Unknown approval_id")
    if approval.status != "approved":
        raise PermissionError("Approval is not approved")
    event_args = approval.arguments
    event = SimulationEngine.load(conn).inject_event(
        event_args["event_type"],
        event_args["target"],
        event_args.get("params") or {},
    )
    payload = {
        "event": event.model_dump(mode="json"),
        "approval_id": approval.approval_id,
        "evidence": [{"type": "event", "id": event.id, "description": "Approved simulated event."}],
    }
    return ok_result("apply_approved_sim_event", payload, read_only=False)

