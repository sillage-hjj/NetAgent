from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.controls.evidence import collect_evidence_refs
from netagent_lab.db import insert_alert, insert_telemetry_sample
from netagent_lab.ingestion.simulated_collectors import collect_sim_all
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.normalization.normalizers import normalize_all
from netagent_lab.orchestration.jobs import MonitoringCycleResult, MonitoringJob
from netagent_lab.reasoning.alerts import evaluate_alerts
from netagent_lab.reasoning.health import evaluate_link_health
from netagent_lab.reasoning.reachability import collect_reachability_matrix
from netagent_lab.sim.schemas import MonitoringSnapshot
from netagent_lab.sim.telemetry import generate_all_telemetry


def run_monitoring_cycle(conn: sqlite3.Connection, focus: dict[str, Any] | None = None) -> MonitoringCycleResult:
    kb = KnowledgeBase.from_db(conn)
    state = kb.get_current_state()
    job = MonitoringJob(
        id=f"monitoring-job-{state.current_tick}",
        created_tick=state.current_tick,
        status="running",
        focus=focus,
    )
    errors: list[str] = []
    collector_results = collect_sim_all(conn)
    normalized_state = normalize_all(collector_results)
    normalized_state_id = kb.save_normalized_state(normalized_state)

    telemetry_samples = generate_all_telemetry(state, state.current_tick)
    for sample in telemetry_samples:
        insert_telemetry_sample(conn, sample)

    reachability = collect_reachability_matrix(kb)
    link_health = {link_id: evaluate_link_health(kb, link_id) for link_id in state.links}
    alerts = evaluate_alerts(kb)
    for alert in alerts:
        insert_alert(conn, alert)

    snapshot = _snapshot_from_workflow(
        kb=kb,
        alerts=alerts,
        reachability=reachability,
    )
    snapshot_id = kb.save_snapshot(snapshot)
    conn.commit()

    reasoning_results = {
        "reachability_matrix": reachability,
        "link_health": link_health,
        "evidence": [ref.model_dump(mode="json") for ref in collect_evidence_refs({"alerts": alerts, "reachability": reachability})],
    }
    return MonitoringCycleResult(
        job_id=job.id,
        tick=state.current_tick,
        collector_results=[result.model_dump(mode="json") for result in collector_results],
        normalized_state_id=normalized_state_id,
        reasoning_results=reasoning_results,
        alerts=alerts,
        snapshot_id=snapshot_id,
        export_refs={
            "snapshot_id": snapshot_id,
            "normalized_state_id": normalized_state_id,
            "telemetry_samples": len(telemetry_samples),
        },
        errors=errors,
    )


def _snapshot_from_workflow(
    kb: KnowledgeBase,
    alerts: list[dict[str, Any]],
    reachability: dict[str, Any],
) -> MonitoringSnapshot:
    state = kb.get_current_state()
    existing_count = len(kb.list_snapshots())
    return MonitoringSnapshot(
        id=f"snapshot-{state.current_tick}-{existing_count + 1:04d}",
        tick=state.current_tick,
        ts=f"tick-{state.current_tick:06d}",
        topology_name=state.topology.name,
        inventory={
            "topology_name": state.topology.name,
            "version": state.topology.version,
            "sites": [site.model_dump(mode="json") for site in state.topology.sites],
            "devices": [device.model_dump(mode="json") for device in state.topology.devices],
            "links": [link.model_dump(mode="json") for link in state.topology.links],
            "services": [service.model_dump(mode="json") for service in state.topology.services],
            "probes": [probe.model_dump(mode="json") for probe in state.topology.probes],
        },
        devices={device.device_id: device.model_dump(mode="json") for device in state.list_devices()},
        interfaces={
            f"{interface.device_id}:{interface.interface_id}": interface.model_dump(mode="json")
            for interface in state.list_interfaces()
        },
        links={link_id: state.link_metadata(link_id) for link_id in state.links},
        services={service.service_id: service.model_dump(mode="json") for service in state.list_services()},
        probes=reachability["probes"],
        paths=reachability,
        alerts=alerts,
        events_since_previous=kb.get_recent_events(),
    )

