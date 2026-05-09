from __future__ import annotations

from typing import Any

from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.sim.pathing import check_service_reachability as _check_service
from netagent_lab.sim.pathing import compute_probe_result as _compute_probe


def check_service_reachability(
    kb: KnowledgeBase,
    source_device: str,
    service_id: str,
) -> dict[str, Any]:
    result = _check_service(kb.get_current_state(), source_device, service_id)
    result.setdefault("evidence", [])
    return result


def compute_probe_result(kb: KnowledgeBase, probe_id: str) -> dict[str, Any]:
    result = _compute_probe(kb.get_current_state(), probe_id)
    result.setdefault("evidence", [])
    return result


def collect_reachability_matrix(kb: KnowledgeBase) -> dict[str, Any]:
    state = kb.get_current_state()
    probes = {probe_id: compute_probe_result(kb, probe_id) for probe_id in state.probes}
    services: dict[str, Any] = {}
    for probe in state.probes.values():
        services[f"{probe.source_device}->{probe.target_service}"] = check_service_reachability(
            kb, probe.source_device, probe.target_service
        )
    evidence = [{"type": "probe", "id": probe_id, "description": "Probe reachability evidence."} for probe_id in probes]
    return {"probes": probes, "services": services, "evidence": evidence}

