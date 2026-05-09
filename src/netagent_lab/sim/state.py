from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from netagent_lab.db import (
    get_current_tick,
    get_metadata,
    list_sim_device_states,
    list_sim_interface_states,
    list_sim_link_states,
    list_sim_probe_defs,
    list_sim_service_states,
    load_topology_from_db,
    set_metadata,
    upsert_sim_device_state,
    upsert_sim_interface_state,
    upsert_sim_link_state,
    upsert_sim_service_state,
)
from netagent_lab.sim.schemas import (
    DeviceRuntimeState,
    InterfaceRuntimeState,
    LinkRuntimeState,
    ServiceRuntimeState,
    SimDevice,
    SimInterface,
    SimLink,
    SimProbe,
    SimService,
    SimTopology,
)


@dataclass
class SimulationStateStore:
    topology: SimTopology
    current_tick: int
    devices: dict[str, DeviceRuntimeState]
    interfaces: dict[str, InterfaceRuntimeState]
    links: dict[str, LinkRuntimeState]
    services: dict[str, ServiceRuntimeState]
    probes: dict[str, SimProbe]
    route_blocks: list[dict[str, Any]]

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> "SimulationStateStore":
        topology = load_topology_from_db(conn)
        route_blocks_json = get_metadata(conn, "route_blocks_json") or "[]"
        return cls(
            topology=topology,
            current_tick=get_current_tick(conn),
            devices={
                item["device_id"]: DeviceRuntimeState.model_validate(item)
                for item in list_sim_device_states(conn)
            },
            interfaces={
                f"{item['device_id']}:{item['interface_id']}": InterfaceRuntimeState.model_validate(item)
                for item in list_sim_interface_states(conn)
            },
            links={item["link_id"]: LinkRuntimeState.model_validate(item) for item in list_sim_link_states(conn)},
            services={
                item["service_id"]: ServiceRuntimeState.model_validate(item)
                for item in list_sim_service_states(conn)
            },
            probes={item["id"]: SimProbe.model_validate(item) for item in list_sim_probe_defs(conn)},
            route_blocks=json.loads(route_blocks_json),
        )

    def save(self, conn: sqlite3.Connection) -> None:
        for device in self.devices.values():
            upsert_sim_device_state(conn, device)
        for interface in self.interfaces.values():
            upsert_sim_interface_state(conn, interface)
        for link in self.links.values():
            upsert_sim_link_state(conn, link)
        for service in self.services.values():
            upsert_sim_service_state(conn, service)
        set_metadata(conn, "route_blocks_json", json.dumps(self.route_blocks, sort_keys=True))
        conn.commit()

    def get_device(self, device_id: str) -> DeviceRuntimeState:
        try:
            return self.devices[device_id]
        except KeyError:
            raise KeyError(f"Unknown device: {device_id}") from None

    def get_interface(self, device_id: str, interface_id: str) -> InterfaceRuntimeState:
        key = f"{device_id}:{interface_id}"
        try:
            return self.interfaces[key]
        except KeyError:
            raise KeyError(f"Unknown interface: {key}") from None

    def get_link(self, link_id: str) -> LinkRuntimeState:
        try:
            return self.links[link_id]
        except KeyError:
            raise KeyError(f"Unknown link: {link_id}") from None

    def get_service(self, service_id: str) -> ServiceRuntimeState:
        try:
            return self.services[service_id]
        except KeyError:
            raise KeyError(f"Unknown service: {service_id}") from None

    def get_probe(self, probe_id: str) -> SimProbe:
        try:
            return self.probes[probe_id]
        except KeyError:
            raise KeyError(f"Unknown probe: {probe_id}") from None

    def list_devices(self) -> list[DeviceRuntimeState]:
        return list(self.devices.values())

    def list_interfaces(self) -> list[InterfaceRuntimeState]:
        return list(self.interfaces.values())

    def list_links(self) -> list[LinkRuntimeState]:
        return list(self.links.values())

    def list_services(self) -> list[ServiceRuntimeState]:
        return list(self.services.values())

    def get_topology_device(self, device_id: str) -> SimDevice:
        for device in self.topology.devices:
            if device.id == device_id:
                return device
        raise KeyError(f"Unknown topology device: {device_id}")

    def get_topology_interface(self, device_id: str, interface_id: str) -> SimInterface:
        device = self.get_topology_device(device_id)
        for interface in device.interfaces:
            if interface.id == interface_id:
                return interface
        raise KeyError(f"Unknown topology interface: {device_id}:{interface_id}")

    def get_topology_link(self, link_id: str) -> SimLink:
        for link in self.topology.links:
            if link.id == link_id:
                return link
        raise KeyError(f"Unknown topology link: {link_id}")

    def get_topology_service(self, service_id: str) -> SimService:
        for service in self.topology.services:
            if service.id == service_id:
                return service
        raise KeyError(f"Unknown topology service: {service_id}")

    def effective_device_up(self, device_id: str) -> bool:
        device = self.get_device(device_id)
        return device.admin_state == "up" and device.oper_state == "up"

    def effective_interface_up(self, device_id: str, interface_id: str) -> bool:
        interface = self.get_interface(device_id, interface_id)
        return (
            self.effective_device_up(device_id)
            and interface.admin_state == "up"
            and interface.oper_state == "up"
        )

    def effective_link_up(self, link_id: str) -> bool:
        runtime = self.get_link(link_id)
        topology = self.get_topology_link(link_id)
        return (
            runtime.admin_state == "up"
            and runtime.oper_state == "up"
            and self.effective_interface_up(topology.endpoint_a.device, topology.endpoint_a.interface)
            and self.effective_interface_up(topology.endpoint_b.device, topology.endpoint_b.interface)
        )

    def connected_links_for_device(self, device_id: str) -> list[SimLink]:
        return [
            link
            for link in self.topology.links
            if link.endpoint_a.device == device_id or link.endpoint_b.device == device_id
        ]

    def link_metadata(self, link_id: str) -> dict[str, Any]:
        topology = self.get_topology_link(link_id)
        runtime = self.get_link(link_id)
        return {
            "link_id": link_id,
            "endpoint_a": topology.endpoint_a.model_dump(mode="json"),
            "endpoint_b": topology.endpoint_b.model_dump(mode="json"),
            "admin_state": runtime.admin_state,
            "oper_state": runtime.oper_state,
            "effective_state": "up" if self.effective_link_up(link_id) else "down",
            "bandwidth_mbps": runtime.bandwidth_mbps,
            "latency_ms": runtime.latency_ms,
            "jitter_ms": runtime.jitter_ms,
            "loss_percent": runtime.loss_percent,
            "utilization_percent": runtime.utilization_percent,
            "error_rate_percent": runtime.error_rate_percent,
            "flap_count": runtime.flap_count,
            "last_change_tick": runtime.last_change_tick,
            "last_event_id": runtime.last_event_id,
            "failure_reason": runtime.failure_reason,
            "tags": topology.tags,
        }

    def route_block_applies(
        self,
        source_device: str,
        *,
        target_service: str | None = None,
        dst_device: str | None = None,
    ) -> dict[str, Any] | None:
        for block in self.route_blocks:
            if block.get("source_device") != source_device:
                continue
            if target_service is not None and block.get("target_service") == target_service:
                return block
            if dst_device is not None and block.get("dst_device") == dst_device:
                return block
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology": self.topology.model_dump(mode="json"),
            "current_tick": self.current_tick,
            "devices": {key: value.model_dump(mode="json") for key, value in self.devices.items()},
            "interfaces": {key: value.model_dump(mode="json") for key, value in self.interfaces.items()},
            "links": {key: self.link_metadata(key) for key in self.links},
            "services": {key: value.model_dump(mode="json") for key, value in self.services.items()},
            "probes": {key: value.model_dump(mode="json") for key, value in self.probes.items()},
            "route_blocks": self.route_blocks,
        }

