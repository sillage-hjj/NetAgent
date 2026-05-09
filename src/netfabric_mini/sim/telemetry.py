from __future__ import annotations

from typing import Any

from netfabric_mini.sim.pathing import compute_probe_result
from netfabric_mini.sim.schemas import TelemetrySample
from netfabric_mini.sim.state import SimulationStateStore


def generate_device_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    samples: list[TelemetrySample] = []
    seq = 1
    for device in state_store.list_devices():
        samples.append(_sample(tick, seq, "device_collector", "device_oper_state", "device", device.device_id, 1.0 if state_store.effective_device_up(device.device_id) else 0.0, None, {}))
        seq += 1
        samples.append(_sample(tick, seq, "device_collector", "cpu_utilization_percent", "device", device.device_id, device.cpu_utilization_percent, "percent", {}))
        seq += 1
        samples.append(_sample(tick, seq, "device_collector", "memory_utilization_percent", "device", device.device_id, device.memory_utilization_percent, "percent", {}))
        seq += 1
    return samples


def generate_interface_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    samples: list[TelemetrySample] = []
    seq = 1
    for interface in state_store.list_interfaces():
        target = f"{interface.device_id}:{interface.interface_id}"
        samples.extend(
            [
                _sample(tick, seq, "interface_collector", "interface_admin_up", "interface", target, 1.0 if interface.admin_state == "up" else 0.0, None, {}),
                _sample(tick, seq + 1, "interface_collector", "interface_oper_up", "interface", target, 1.0 if state_store.effective_interface_up(interface.device_id, interface.interface_id) else 0.0, None, {}),
                _sample(tick, seq + 2, "interface_collector", "interface_utilization_percent", "interface", target, interface.utilization_percent, "percent", {}),
                _sample(tick, seq + 3, "interface_collector", "interface_rx_errors", "interface", target, float(interface.rx_errors), "count", {}),
                _sample(tick, seq + 4, "interface_collector", "interface_tx_errors", "interface", target, float(interface.tx_errors), "count", {}),
            ]
        )
        seq += 5
    return samples


def generate_link_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    samples: list[TelemetrySample] = []
    seq = 1
    for link_id in state_store.links:
        metadata = state_store.link_metadata(link_id)
        labels = {"link_metadata": metadata}
        link = state_store.get_link(link_id)
        metrics = [
            ("link_admin_up", 1.0 if link.admin_state == "up" else 0.0, None),
            ("link_oper_up", 1.0 if state_store.effective_link_up(link_id) else 0.0, None),
            ("link_latency_ms", link.latency_ms, "ms"),
            ("link_jitter_ms", link.jitter_ms, "ms"),
            ("link_loss_percent", link.loss_percent, "percent"),
            ("link_utilization_percent", link.utilization_percent, "percent"),
            ("link_error_rate_percent", link.error_rate_percent, "percent"),
            ("link_flap_count", float(link.flap_count), "count"),
        ]
        for metric, value, unit in metrics:
            samples.append(_sample(tick, seq, "link_collector", metric, "link", link_id, value, unit, labels))
            seq += 1
    return samples


def generate_service_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    samples: list[TelemetrySample] = []
    seq = 1
    for service in state_store.list_services():
        samples.extend(
            [
                _sample(tick, seq, "service_collector", "service_up", "service", service.service_id, 1.0 if service.status != "down" else 0.0, None, {}),
                _sample(tick, seq + 1, "service_collector", "service_degraded", "service", service.service_id, 1.0 if service.status == "degraded" else 0.0, None, {}),
                _sample(tick, seq + 2, "service_collector", "service_latency_ms", "service", service.service_id, float(service.latency_ms or 0.0), "ms", {}),
                _sample(tick, seq + 3, "service_collector", "service_loss_percent", "service", service.service_id, float(service.loss_percent or 0.0), "percent", {}),
            ]
        )
        seq += 4
    return samples


def generate_probe_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    samples: list[TelemetrySample] = []
    seq = 1
    for probe_id in state_store.probes:
        result = compute_probe_result(state_store, probe_id)
        labels = {"probe_result": result}
        metrics = [
            ("probe_reachable", 1.0 if result["reachable"] else 0.0, None),
            ("probe_degraded", 1.0 if result["degraded"] else 0.0, None),
            ("probe_latency_ms", float(result["latency_ms"] or 0.0), "ms"),
            ("probe_loss_percent", float(result["loss_percent"] or 0.0), "percent"),
            ("probe_max_utilization_percent", float(result["max_utilization_percent"] or 0.0), "percent"),
        ]
        for metric, value, unit in metrics:
            samples.append(_sample(tick, seq, "probe_collector", metric, "probe", probe_id, value, unit, labels))
            seq += 1
    return samples


def generate_all_telemetry(state_store: SimulationStateStore, tick: int) -> list[TelemetrySample]:
    raw_samples = (
        generate_device_telemetry(state_store, tick)
        + generate_interface_telemetry(state_store, tick)
        + generate_link_telemetry(state_store, tick)
        + generate_service_telemetry(state_store, tick)
        + generate_probe_telemetry(state_store, tick)
    )
    normalized: list[TelemetrySample] = []
    for index, sample in enumerate(raw_samples, start=1):
        normalized.append(sample.model_copy(update={"id": f"telemetry-{tick}-{index:04d}"}))
    return normalized


def _sample(
    tick: int,
    sequence: int,
    source: str,
    metric: str,
    target_type: str,
    target_id: str,
    value: float,
    unit: str | None,
    labels: dict[str, Any],
) -> TelemetrySample:
    return TelemetrySample(
        id=f"telemetry-{tick}-{sequence:04d}",
        tick=tick,
        ts=f"tick-{tick:06d}",
        source=source,
        metric=metric,
        target_type=target_type,
        target_id=target_id,
        value=float(value),
        unit=unit,
        labels=labels,
    )

