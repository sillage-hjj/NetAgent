from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import (
    get_current_tick,
    insert_sim_event,
    next_sim_sequence,
    set_current_tick,
)
from netagent_lab.sim.events import SUPPORTED_EVENTS, target_type_for_event
from netagent_lab.sim.schemas import SimulationEvent
from netagent_lab.sim.state import SimulationStateStore


class SimulationEngine:
    def __init__(self, conn: sqlite3.Connection, state_store: SimulationStateStore):
        self.conn = conn
        self.state_store = state_store

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> "SimulationEngine":
        return cls(conn, SimulationStateStore.load(conn))

    def tick(self, steps: int = 1) -> dict[str, Any]:
        if steps < 1:
            raise ValueError("steps must be >= 1")
        old_tick = get_current_tick(self.conn)
        new_tick = old_tick + steps
        set_current_tick(self.conn, new_tick)
        self.state_store.current_tick = new_tick
        return {"old_tick": old_tick, "new_tick": new_tick, "steps": steps}

    def inject_event(self, event_type: str, target: str, params: dict[str, Any] | None = None) -> SimulationEvent:
        params = params or {}
        if event_type not in SUPPORTED_EVENTS:
            raise ValueError(f"Unsupported event type: {event_type}")
        tick = get_current_tick(self.conn)
        sequence = next_sim_sequence(self.conn, "sim_events", tick)
        event = SimulationEvent(
            id=f"event-{tick}-{sequence:04d}",
            tick=tick,
            ts=_sim_ts(tick),
            event_type=event_type,
            target_type=target_type_for_event(event_type),
            target_id=target,
            severity=_severity_for_event(event_type),
            params=params,
            description=_description(event_type, target, params),
        )
        self.apply_event(event)
        insert_sim_event(self.conn, event)
        return event

    def apply_event(self, event: SimulationEvent) -> dict[str, Any]:
        event_type = event.event_type
        if event_type == "link_down":
            link = self.state_store.get_link(event.target_id)
            link.oper_state = "down"
            link.failure_reason = event.params.get("reason")
            self._mark_link(link.link_id, event)
        elif event_type == "link_up":
            link = self.state_store.get_link(event.target_id)
            link.oper_state = "up"
            link.failure_reason = None
            self._mark_link(link.link_id, event)
        elif event_type == "link_flap":
            count = int(event.params.get("count", 1))
            _require_range("count", count, minimum=1)
            link = self.state_store.get_link(event.target_id)
            link.flap_count += count
            link.oper_state = "up"
            link.error_rate_percent = min(100.0, link.error_rate_percent + count)
            self._mark_link(link.link_id, event)
        elif event_type == "set_link_latency":
            value = float(event.params["latency_ms"])
            _require_range("latency_ms", value, minimum=0)
            link = self.state_store.get_link(event.target_id)
            link.latency_ms = value
            self._mark_link(link.link_id, event)
        elif event_type == "set_link_loss":
            value = float(event.params["loss_percent"])
            _require_range("loss_percent", value, minimum=0, maximum=100)
            link = self.state_store.get_link(event.target_id)
            link.loss_percent = value
            self._mark_link(link.link_id, event)
        elif event_type == "set_link_utilization":
            value = float(event.params["utilization_percent"])
            _require_range("utilization_percent", value, minimum=0, maximum=100)
            link = self.state_store.get_link(event.target_id)
            link.utilization_percent = value
            self._mark_link(link.link_id, event)
        elif event_type == "set_link_errors":
            value = float(event.params["error_rate_percent"])
            _require_range("error_rate_percent", value, minimum=0, maximum=100)
            link = self.state_store.get_link(event.target_id)
            link.error_rate_percent = value
            self._mark_link(link.link_id, event)
        elif event_type == "device_down":
            device = self.state_store.get_device(event.target_id)
            device.oper_state = "down"
            self._mark_device(device.device_id, event)
        elif event_type == "device_up":
            device = self.state_store.get_device(event.target_id)
            device.oper_state = "up"
            self._mark_device(device.device_id, event)
        elif event_type == "set_device_cpu":
            value = float(event.params["cpu_utilization_percent"])
            _require_range("cpu_utilization_percent", value, minimum=0, maximum=100)
            device = self.state_store.get_device(event.target_id)
            device.cpu_utilization_percent = value
            self._mark_device(device.device_id, event)
        elif event_type == "set_device_memory":
            value = float(event.params["memory_utilization_percent"])
            _require_range("memory_utilization_percent", value, minimum=0, maximum=100)
            device = self.state_store.get_device(event.target_id)
            device.memory_utilization_percent = value
            self._mark_device(device.device_id, event)
        elif event_type in {"interface_down", "interface_up"}:
            device_id, interface_id = _parse_interface_target(event.target_id)
            interface = self.state_store.get_interface(device_id, interface_id)
            interface.oper_state = "down" if event_type == "interface_down" else "up"
            interface.last_change_tick = event.tick
            interface.last_event_id = event.id
        elif event_type in {"service_down", "service_up", "service_degraded"}:
            service = self.state_store.get_service(event.target_id)
            if event_type == "service_down":
                service.status = "down"
            elif event_type == "service_up":
                service.status = "up"
                service.latency_ms = None
                service.loss_percent = None
            else:
                latency = float(event.params.get("latency_ms", 150.0))
                loss = float(event.params.get("loss_percent", 0.0))
                _require_range("latency_ms", latency, minimum=0)
                _require_range("loss_percent", loss, minimum=0, maximum=100)
                service.status = "degraded"
                service.latency_ms = latency
                service.loss_percent = loss
            service.last_change_tick = event.tick
            service.last_event_id = event.id
        elif event_type == "route_withdrawal":
            source = event.params["source_device"]
            self.state_store.get_device(source)
            block = {
                "id": event.target_id,
                "source_device": source,
                "target_service": event.params.get("target_service"),
                "dst_device": event.params.get("dst_device"),
                "reason": event.params.get("reason", "route withdrawn"),
                "last_event_id": event.id,
            }
            if not block["target_service"] and not block["dst_device"]:
                raise ValueError("route_withdrawal requires target_service or dst_device")
            if block["target_service"]:
                self.state_store.get_service(block["target_service"])
            if block["dst_device"]:
                self.state_store.get_device(block["dst_device"])
            self.state_store.route_blocks = [
                existing for existing in self.state_store.route_blocks if existing["id"] != event.target_id
            ]
            self.state_store.route_blocks.append(block)
        elif event_type == "route_restore":
            before = len(self.state_store.route_blocks)
            self.state_store.route_blocks = [
                existing for existing in self.state_store.route_blocks if existing["id"] != event.target_id
            ]
            if len(self.state_store.route_blocks) == before:
                raise KeyError(f"Unknown route block: {event.target_id}")
        else:
            raise ValueError(f"Unsupported event type: {event_type}")
        self.state_store.save(self.conn)
        return {"ok": True, "event_id": event.id}

    def run_scenario(self, name: str) -> dict[str, Any]:
        from netagent_lab.sim.scenarios import run_scenario

        return run_scenario(name)

    def _mark_link(self, link_id: str, event: SimulationEvent) -> None:
        link = self.state_store.get_link(link_id)
        link.last_change_tick = event.tick
        link.last_event_id = event.id

    def _mark_device(self, device_id: str, event: SimulationEvent) -> None:
        device = self.state_store.get_device(device_id)
        device.last_change_tick = event.tick
        device.last_event_id = event.id


def _parse_interface_target(target: str) -> tuple[str, str]:
    if ":" not in target:
        raise ValueError("Interface target must be device_id:interface_id")
    return target.split(":", 1)


def _require_range(name: str, value: float, *, minimum: float, maximum: float | None = None) -> None:
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")


def _severity_for_event(event_type: str) -> str:
    if event_type in {"link_down", "device_down", "service_down", "route_withdrawal"}:
        return "critical"
    if event_type in {
        "link_flap",
        "set_link_latency",
        "set_link_loss",
        "set_link_utilization",
        "set_link_errors",
        "set_device_cpu",
        "set_device_memory",
        "interface_down",
        "service_degraded",
    }:
        return "warning"
    return "info"


def _description(event_type: str, target: str, params: dict[str, Any]) -> str:
    if params:
        return f"Applied {event_type} to {target} with params {params}."
    return f"Applied {event_type} to {target}."


def _sim_ts(tick: int) -> str:
    return f"tick-{tick:06d}"

