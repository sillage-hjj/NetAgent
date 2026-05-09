from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

import typer

from netagent_lab.db import (
    connect_db,
    get_snapshot,
    init_sim_db,
    initialize_runtime_state,
    list_snapshots,
)
from netagent_lab.monitoring.collectors import collect_link_states, collect_probe_results
from netagent_lab.monitoring.diff import diff_snapshot_aliases
from netagent_lab.monitoring.monitor import create_snapshot_only, run_monitor_loop, run_monitor_once
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.exporters import (
    export_current_state_json,
    export_events_jsonl,
    export_latest_snapshot_json,
    export_llm_ready_context,
    export_telemetry_jsonl,
)
from netagent_lab.sim.scenarios import run_scenario
from netagent_lab.sim.state import SimulationStateStore
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, list_topologies, load_topology


sim_app = typer.Typer(name="sim", help="Configurable offline network simulator.")


@sim_app.command("list-topologies")
def list_topologies_command() -> None:
    for item in list_topologies(DEFAULT_TOPOLOGIES_DIR):
        status = "valid" if item.get("valid") else "invalid"
        typer.echo(f"{item['name']}\t{status}\t{item['path']}")


@sim_app.command("validate")
def validate_command(topology: Path = typer.Option(..., "--topology")) -> None:
    loaded = load_topology(topology)
    typer.echo(f"valid: {loaded.name} ({len(loaded.devices)} devices, {len(loaded.links)} links)")


@sim_app.command("init")
def init_command(
    topology: Path = typer.Option(..., "--topology"),
    db: Path = typer.Option(..., "--db"),
) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = init_sim_db(db)
    loaded = load_topology(topology)
    initialize_runtime_state(conn, loaded)
    conn.close()
    typer.echo(f"Initialized simulation DB {db} with topology {loaded.name}")


@sim_app.command("state")
def state_command(db: Path = typer.Option(..., "--db")) -> None:
    conn = connect_db(db)
    state = SimulationStateStore.load(conn)
    links = collect_link_states(conn)["result"]
    probes = collect_probe_results(conn)["result"]
    summary = {
        "topology_name": state.topology.name,
        "tick": state.current_tick,
        "device_count": len(state.devices),
        "link_count": len(state.links),
        "services": list(state.services),
        "probes": probes,
        "links": {
            link_id: {
                "oper_state": link["oper_state"],
                "effective_state": link["effective_state"],
                "latency_ms": link["latency_ms"],
                "loss_percent": link["loss_percent"],
                "utilization_percent": link["utilization_percent"],
            }
            for link_id, link in links.items()
        },
    }
    conn.close()
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))


@sim_app.command("tick")
def tick_command(
    db: Path = typer.Option(..., "--db"),
    steps: int = typer.Option(1, "--steps"),
) -> None:
    conn = connect_db(db)
    result = SimulationEngine.load(conn).tick(steps)
    conn.close()
    typer.echo(json.dumps(result, sort_keys=True))


@sim_app.command("inject")
def inject_command(
    db: Path = typer.Option(..., "--db"),
    event: str = typer.Option(..., "--event"),
    target: Optional[str] = typer.Option(None, "--target"),
    link: Optional[str] = typer.Option(None, "--link"),
    params: List[str] = typer.Option([], "--param"),
) -> None:
    resolved_target = target or link
    if not resolved_target:
        raise typer.BadParameter("--target is required")
    conn = connect_db(db)
    sim_event = SimulationEngine.load(conn).inject_event(event, resolved_target, _parse_params(params))
    conn.close()
    typer.echo(json.dumps(sim_event.model_dump(mode="json"), sort_keys=True))


@sim_app.command("monitor")
def monitor_command(
    db: Path = typer.Option(..., "--db"),
    once: bool = typer.Option(False, "--once"),
    interval_seconds: float = typer.Option(1.0, "--interval-seconds"),
    max_iterations: Optional[int] = typer.Option(None, "--max-iterations"),
) -> None:
    conn = connect_db(db)
    if once or max_iterations is None:
        result = run_monitor_once(conn)
    else:
        result = run_monitor_loop(conn, interval_seconds, max_iterations=max_iterations)
    conn.close()
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@sim_app.command("snapshot")
def snapshot_command(db: Path = typer.Option(..., "--db")) -> None:
    conn = connect_db(db)
    snapshot = create_snapshot_only(conn)
    conn.close()
    typer.echo(snapshot.id)


@sim_app.command("snapshots")
def snapshots_command(db: Path = typer.Option(..., "--db")) -> None:
    conn = connect_db(db)
    snapshots = list_snapshots(conn)
    conn.close()
    typer.echo(json.dumps(snapshots, indent=2, sort_keys=True))


@sim_app.command("diff")
def diff_command(
    db: Path = typer.Option(..., "--db"),
    from_snapshot: str = typer.Option("latest-1", "--from"),
    to_snapshot: str = typer.Option("latest", "--to"),
) -> None:
    conn = connect_db(db)
    diff = diff_snapshot_aliases(conn, from_snapshot, to_snapshot)
    conn.close()
    typer.echo(json.dumps(diff, indent=2, sort_keys=True))


@sim_app.command("export")
def export_command(
    db: Path = typer.Option(..., "--db"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    conn = connect_db(db)
    if output_format == "json":
        payload: Any = export_current_state_json(conn)
    elif output_format == "latest-snapshot":
        payload = export_latest_snapshot_json(conn)
    elif output_format == "events-jsonl":
        typer.echo(export_events_jsonl(conn))
        conn.close()
        return
    elif output_format == "telemetry-jsonl":
        typer.echo(export_telemetry_jsonl(conn))
        conn.close()
        return
    elif output_format in {"llm-context", "llm-ready"}:
        payload = export_llm_ready_context(conn)
    else:
        raise typer.BadParameter("format must be json, latest-snapshot, events-jsonl, telemetry-jsonl, llm-context, or llm-ready")
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@sim_app.command("scenario")
def scenario_command(name: str = typer.Option(..., "--name")) -> None:
    result = run_scenario(name)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


def _parse_params(params: List[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in params:
        if "=" not in item:
            raise typer.BadParameter(f"param must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        parsed[key] = _coerce_value(value)
    return parsed


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
