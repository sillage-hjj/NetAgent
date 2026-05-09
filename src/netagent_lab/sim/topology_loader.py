from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from netagent_lab.sim.schemas import SimTopology


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TOPOLOGIES_DIR = PROJECT_ROOT / "data" / "topologies"


def load_topology(path: str | Path) -> SimTopology:
    topology_path = Path(path)
    if not topology_path.exists():
        raise FileNotFoundError(f"Topology file not found: {topology_path}")
    try:
        data = yaml.safe_load(topology_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed topology YAML in {topology_path}: {exc}") from exc

    topology = SimTopology.model_validate(data)
    errors = validate_topology(topology)
    if errors:
        raise ValueError("; ".join(errors))
    return topology


def validate_topology(topology: SimTopology) -> list[str]:
    errors: list[str] = []
    device_ids = [device.id for device in topology.devices]
    link_ids = [link.id for link in topology.links]
    service_ids = [service.id for service in topology.services]

    _add_duplicate_errors(errors, "Device ID", device_ids)
    _add_duplicate_errors(errors, "Link ID", link_ids)
    _add_duplicate_errors(errors, "Service ID", service_ids)

    device_map = {device.id: device for device in topology.devices}
    interface_keys: set[tuple[str, str]] = set()
    connected_interfaces: dict[tuple[str, str], str] = {}

    for device in topology.devices:
        interface_ids = [interface.id for interface in device.interfaces]
        _add_duplicate_errors(errors, f"Interface ID on {device.id}", interface_ids)
        for interface_id in interface_ids:
            interface_keys.add((device.id, interface_id))

    for link in topology.links:
        endpoints = [link.endpoint_a, link.endpoint_b]
        for endpoint in endpoints:
            if endpoint.device not in device_map:
                errors.append(f"Link {link.id} references missing device {endpoint.device}")
                continue
            key = (endpoint.device, endpoint.interface)
            if key not in interface_keys:
                errors.append(
                    f"Link {link.id} references missing interface "
                    f"{endpoint.device}:{endpoint.interface}"
                )
                continue
            if key in connected_interfaces:
                errors.append(
                    f"Interface {endpoint.device}:{endpoint.interface} is connected to both "
                    f"{connected_interfaces[key]} and {link.id}"
                )
            connected_interfaces[key] = link.id

        if link.loss_percent < 0 or link.loss_percent > 100:
            errors.append(f"Link {link.id} loss_percent must be between 0 and 100")
        if link.utilization_percent < 0 or link.utilization_percent > 100:
            errors.append(f"Link {link.id} utilization_percent must be between 0 and 100")
        if link.latency_ms < 0:
            errors.append(f"Link {link.id} latency_ms must be >= 0")
        if link.bandwidth_mbps <= 0:
            errors.append(f"Link {link.id} bandwidth_mbps must be > 0")

    for service in topology.services:
        if service.device not in device_map:
            errors.append(f"Service {service.id} references missing device {service.device}")

    service_set = set(service_ids)
    for probe in topology.probes:
        if probe.source_device not in device_map:
            errors.append(f"Probe {probe.id} references missing source device {probe.source_device}")
        if probe.target_service not in service_set:
            errors.append(f"Probe {probe.id} references missing target service {probe.target_service}")

    return errors


def list_topologies(directory: str | Path = DEFAULT_TOPOLOGIES_DIR) -> list[dict[str, Any]]:
    root = Path(directory)
    if not root.exists():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        try:
            topology = load_topology(path)
            results.append(
                {
                    "name": topology.name,
                    "path": str(path),
                    "description": topology.description,
                    "version": topology.version,
                    "devices": len(topology.devices),
                    "links": len(topology.links),
                    "services": len(topology.services),
                    "valid": True,
                }
            )
        except Exception as exc:
            results.append({"name": path.stem, "path": str(path), "valid": False, "error": str(exc)})
    return results


def _add_duplicate_errors(errors: list[str], label: str, values: list[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    for value in sorted(duplicates):
        errors.append(f"{label} must be unique: {value}")

