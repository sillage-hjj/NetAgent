from __future__ import annotations

from typing import Any

import networkx as nx

from netagent_lab.sim.state import SimulationStateStore


def build_available_graph(state_store: SimulationStateStore) -> nx.Graph:
    graph = nx.Graph()
    for device in state_store.topology.devices:
        graph.add_node(device.id)
    for topology_link in state_store.topology.links:
        if not state_store.effective_link_up(topology_link.id):
            continue
        runtime = state_store.get_link(topology_link.id)
        graph.add_edge(
            topology_link.endpoint_a.device,
            topology_link.endpoint_b.device,
            id=topology_link.id,
            weight=topology_link.weight,
            latency_ms=runtime.latency_ms,
            loss_percent=runtime.loss_percent,
            utilization_percent=runtime.utilization_percent,
            error_rate_percent=runtime.error_rate_percent,
        )
    return graph


def infer_simulated_path(
    state_store: SimulationStateStore,
    src_device: str,
    dst_device: str,
) -> dict[str, Any]:
    graph = build_available_graph(state_store)
    evidence = [
        {
            "type": "path_result",
            "id": f"sim-path-{src_device}-to-{dst_device}-tick-{state_store.current_tick}",
            "description": "Simulated path inference used effective-up links only.",
        }
    ]
    try:
        path = nx.shortest_path(graph, src_device, dst_device, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        blocking_reasons = _blocking_reasons(state_store)
        evidence.extend(
            {
                "type": reason["type"],
                "id": reason["id"],
                "description": reason["description"],
            }
            for reason in blocking_reasons
        )
        return {
            "reachable": False,
            "src_device": src_device,
            "dst_device": dst_device,
            "path": [],
            "links": [],
            "total_latency_ms": None,
            "max_loss_percent": None,
            "max_utilization_percent": None,
            "degraded": False,
            "degradation_reasons": [],
            "blocking_reasons": blocking_reasons,
            "evidence": evidence,
        }

    link_ids = [graph.edges[left, right]["id"] for left, right in zip(path, path[1:])]
    links = [state_store.get_link(link_id) for link_id in link_ids]
    total_latency = sum(link.latency_ms for link in links)
    max_loss = max((link.loss_percent for link in links), default=0.0)
    max_util = max((link.utilization_percent for link in links), default=0.0)
    max_error = max((link.error_rate_percent for link in links), default=0.0)
    degradation_reasons = []
    if total_latency > 100:
        degradation_reasons.append({"type": "high_latency", "value": total_latency, "threshold": 100})
    if max_loss > 5:
        degradation_reasons.append({"type": "packet_loss", "value": max_loss, "threshold": 5})
    if max_util > 85:
        degradation_reasons.append({"type": "high_utilization", "value": max_util, "threshold": 85})
    if max_error > 5:
        degradation_reasons.append({"type": "interface_errors", "value": max_error, "threshold": 5})
    evidence.extend(
        {
            "type": "link",
            "id": link_id,
            "description": f"Effective-up simulated link {link_id} is on the selected path.",
        }
        for link_id in link_ids
    )
    return {
        "reachable": True,
        "src_device": src_device,
        "dst_device": dst_device,
        "path": path,
        "links": link_ids,
        "total_latency_ms": total_latency,
        "max_loss_percent": max_loss,
        "max_utilization_percent": max_util,
        "degraded": bool(degradation_reasons),
        "degradation_reasons": degradation_reasons,
        "blocking_reasons": [],
        "evidence": evidence,
    }


def check_service_reachability(
    state_store: SimulationStateStore,
    source_device: str,
    service_id: str,
) -> dict[str, Any]:
    service_topology = state_store.get_topology_service(service_id)
    service_runtime = state_store.get_service(service_id)
    route_block = state_store.route_block_applies(
        source_device,
        target_service=service_id,
        dst_device=service_topology.device,
    )
    if route_block is not None:
        return {
            "reachable": False,
            "service_id": service_id,
            "source_device": source_device,
            "target_device": service_topology.device,
            "path_result": None,
            "degraded": False,
            "blocking_reasons": [
                {"type": "route_withdrawal", "id": route_block["id"], "description": route_block["reason"]}
            ],
            "evidence": [
                {
                    "type": "route_block",
                    "id": route_block["id"],
                    "description": route_block["reason"],
                }
            ],
        }
    if service_runtime.status == "down" or not state_store.effective_device_up(service_topology.device):
        return {
            "reachable": False,
            "service_id": service_id,
            "source_device": source_device,
            "target_device": service_topology.device,
            "path_result": None,
            "degraded": False,
            "blocking_reasons": [
                {"type": "service_down", "id": service_id, "description": "Service or hosting device is down."}
            ],
            "evidence": [
                {
                    "type": "service",
                    "id": service_id,
                    "description": "Service runtime state or hosting device is down.",
                }
            ],
        }
    path_result = infer_simulated_path(state_store, source_device, service_topology.device)
    degraded = bool(path_result["degraded"] or service_runtime.status == "degraded")
    reasons = list(path_result["degradation_reasons"])
    if service_runtime.status == "degraded":
        reasons.append({"type": "service_degraded", "id": service_id})
    return {
        "reachable": path_result["reachable"],
        "service_id": service_id,
        "source_device": source_device,
        "target_device": service_topology.device,
        "path_result": path_result,
        "degraded": degraded if path_result["reachable"] else False,
        "blocking_reasons": path_result["blocking_reasons"],
        "degradation_reasons": reasons,
        "evidence": path_result["evidence"],
    }


def compute_probe_result(state_store: SimulationStateStore, probe_id: str) -> dict[str, Any]:
    probe = state_store.get_probe(probe_id)
    if not probe.enabled:
        return {
            "probe_id": probe_id,
            "reachable": False,
            "degraded": False,
            "disabled": True,
            "latency_ms": None,
            "loss_percent": None,
            "max_utilization_percent": None,
            "evidence": [{"type": "probe", "id": probe_id, "description": "Probe is disabled."}],
        }
    reachability = check_service_reachability(state_store, probe.source_device, probe.target_service)
    path = reachability.get("path_result") or {}
    return {
        "probe_id": probe_id,
        "name": probe.name,
        "source_device": probe.source_device,
        "target_service": probe.target_service,
        "reachable": reachability["reachable"],
        "degraded": reachability.get("degraded", False),
        "disabled": False,
        "latency_ms": path.get("total_latency_ms"),
        "loss_percent": path.get("max_loss_percent"),
        "max_utilization_percent": path.get("max_utilization_percent"),
        "blocking_reasons": reachability.get("blocking_reasons", []),
        "degradation_reasons": reachability.get("degradation_reasons", []),
        "evidence": reachability["evidence"],
    }


def _blocking_reasons(state_store: SimulationStateStore) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    for device in state_store.list_devices():
        if device.admin_state == "down" or device.oper_state == "down":
            reasons.append(
                {
                    "type": "device_down",
                    "id": device.device_id,
                    "description": f"Device {device.device_id} is not effective-up.",
                }
            )
    for topology_link in state_store.topology.links:
        if not state_store.effective_link_up(topology_link.id):
            reasons.append(
                {
                    "type": "link_down",
                    "id": topology_link.id,
                    "description": f"Link {topology_link.id} is not effective-up.",
                }
            )
    return reasons

