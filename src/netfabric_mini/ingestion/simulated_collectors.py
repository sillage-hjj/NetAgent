from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.db import get_current_tick, list_sim_events, list_telemetry_samples
from netfabric_mini.ingestion.collector_contracts import CollectorResult
from netfabric_mini.normalization.schemas import EvidenceRef
from netfabric_mini.sim.pathing import check_service_reachability, compute_probe_result
from netfabric_mini.sim.state import SimulationStateStore


def collect_sim_inventory(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {
        "topology_name": state.topology.name,
        "version": state.topology.version,
        "sites": [site.model_dump(mode="json") for site in state.topology.sites],
        "devices": [device.model_dump(mode="json") for device in state.topology.devices],
        "links": [link.model_dump(mode="json") for link in state.topology.links],
        "services": [service.model_dump(mode="json") for service in state.topology.services],
        "probes": [probe.model_dump(mode="json") for probe in state.topology.probes],
    }
    return _result("collect_sim_inventory", state.current_tick, result, [("topology", state.topology.name)])


def collect_sim_device_states(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {device.device_id: device.model_dump(mode="json") for device in state.list_devices()}
    return _result("collect_sim_device_states", state.current_tick, result, [("device", key) for key in result])


def collect_sim_interface_states(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {
        f"{interface.device_id}:{interface.interface_id}": interface.model_dump(mode="json")
        for interface in state.list_interfaces()
    }
    return _result("collect_sim_interface_states", state.current_tick, result, [("interface", key) for key in result])


def collect_sim_link_states(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {link_id: state.link_metadata(link_id) for link_id in state.links}
    evidence = [
        EvidenceRef(
            type="link",
            id=link_id,
            description=f"Simulated link state at tick {state.current_tick}.",
        )
        for link_id in result
    ]
    return CollectorResult(
        collector="collect_sim_link_states",
        source="simulation",
        ok=True,
        tick=state.current_tick,
        result=result,
        evidence=evidence,
        errors=[],
    )


def collect_sim_service_states(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {service.service_id: service.model_dump(mode="json") for service in state.list_services()}
    return _result("collect_sim_service_states", state.current_tick, result, [("service", key) for key in result])


def collect_sim_probe_results(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    result = {probe_id: compute_probe_result(state, probe_id) for probe_id in state.probes}
    return _result("collect_sim_probe_results", state.current_tick, result, [("probe", key) for key in result])


def collect_sim_recent_events(conn: sqlite3.Connection, since_tick: int | None = None) -> CollectorResult:
    tick = get_current_tick(conn)
    events = list_sim_events(conn, since_tick)
    return _result("collect_sim_recent_events", tick, events, [("event", event["id"]) for event in events])


def collect_sim_recent_telemetry(conn: sqlite3.Connection, since_tick: int | None = None) -> CollectorResult:
    tick = get_current_tick(conn)
    samples = list_telemetry_samples(conn, since_tick)
    return _result(
        "collect_sim_recent_telemetry",
        tick,
        samples,
        [("telemetry", sample["id"]) for sample in samples],
    )


def collect_sim_reachability_matrix(conn: sqlite3.Connection) -> CollectorResult:
    state = SimulationStateStore.load(conn)
    probes = {probe_id: compute_probe_result(state, probe_id) for probe_id in state.probes}
    services: dict[str, Any] = {}
    for probe in state.probes.values():
        services[f"{probe.source_device}->{probe.target_service}"] = check_service_reachability(
            state, probe.source_device, probe.target_service
        )
    return _result(
        "collect_sim_reachability_matrix",
        state.current_tick,
        {"probes": probes, "services": services},
        [("probe", key) for key in probes],
    )


def collect_sim_all(conn: sqlite3.Connection) -> list[CollectorResult]:
    return [
        collect_sim_inventory(conn),
        collect_sim_device_states(conn),
        collect_sim_interface_states(conn),
        collect_sim_link_states(conn),
        collect_sim_service_states(conn),
        collect_sim_probe_results(conn),
        collect_sim_recent_events(conn),
        collect_sim_recent_telemetry(conn),
    ]


def _result(
    collector: str,
    tick: int,
    result: dict[str, Any] | list[Any],
    evidence_pairs: list[tuple[str, str]],
) -> CollectorResult:
    return CollectorResult(
        collector=collector,
        source="simulation",
        ok=True,
        tick=tick,
        result=result,
        evidence=[
            EvidenceRef(type=item_type, id=item_id, description=f"{collector} evidence: {item_id}.")
            for item_type, item_id in evidence_pairs
        ],
        errors=[],
    )

