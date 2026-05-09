from __future__ import annotations

import sqlite3

from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.orchestration.monitoring_workflow import run_monitoring_cycle
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def prepare_agent_scenario_db(name: str) -> sqlite3.Connection:
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    run_monitoring_cycle(conn)
    engine = SimulationEngine.load(conn)
    if name == "link_failure":
        engine.inject_event("link_down", "link_r1_r2", {"reason": "fiber_cut"})
    elif name == "congestion":
        engine.inject_event("set_link_utilization", "link_r1_r2", {"utilization_percent": 93})
        engine.inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
        engine.inject_event("set_link_latency", "link_r1_r2", {"latency_ms": 120})
    elif name == "route_withdrawal":
        engine.inject_event(
            "route_withdrawal",
            "routeblock-1",
            {"source_device": "client_zurich", "target_service": "app_b", "reason": "bgp_withdrawal"},
        )
    elif name == "healthy_network_summary":
        pass
    elif name == "insufficient_evidence":
        pass
    else:
        raise ValueError(f"Unknown agent scenario: {name}")
    engine.tick(1)
    run_monitoring_cycle(conn)
    return conn


def scenario_question(name: str) -> str:
    if name == "congestion":
        return "Why is App-B slow from Zurich?"
    if name == "route_withdrawal":
        return "Why is App-B unreachable from Zurich after a route change?"
    if name == "healthy_network_summary":
        return "Summarize the current network health."
    if name == "insufficient_evidence":
        return "What caused the issue without running tools?"
    return "Why is App-B unreachable from Zurich?"

