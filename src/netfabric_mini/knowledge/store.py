from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from netfabric_mini.db import (
    get_current_tick,
    get_normalized_state,
    get_snapshot,
    insert_normalized_state,
    insert_snapshot,
    list_alerts,
    list_normalized_observations,
    list_sim_events,
    list_snapshots,
    list_telemetry_samples,
)
from netfabric_mini.normalization.schemas import EvidenceRef, NormalizedNetworkState
from netfabric_mini.sim.schemas import MonitoringSnapshot, SimTopology
from netfabric_mini.sim.state import SimulationStateStore


@dataclass
class KnowledgeBase:
    conn: sqlite3.Connection

    @classmethod
    def from_db(cls, conn: sqlite3.Connection) -> "KnowledgeBase":
        return cls(conn)

    def get_current_tick(self) -> int:
        return get_current_tick(self.conn)

    def get_topology(self) -> SimTopology:
        return SimulationStateStore.load(self.conn).topology

    def get_current_state(self) -> SimulationStateStore:
        return SimulationStateStore.load(self.conn)

    def get_device(self, device_id: str) -> dict[str, Any]:
        return self.get_current_state().get_device(device_id).model_dump(mode="json")

    def get_interface(self, device_id: str, interface_id: str) -> dict[str, Any]:
        return self.get_current_state().get_interface(device_id, interface_id).model_dump(mode="json")

    def get_link(self, link_id: str) -> dict[str, Any]:
        return self.get_current_state().link_metadata(link_id)

    def get_service(self, service_id: str) -> dict[str, Any]:
        state = self.get_current_state()
        runtime = state.get_service(service_id).model_dump(mode="json")
        topology = state.get_topology_service(service_id).model_dump(mode="json")
        return {"topology": topology, "runtime": runtime}

    def get_recent_events(self, since_tick: int | None = None) -> list[dict[str, Any]]:
        return list_sim_events(self.conn, since_tick)

    def get_recent_telemetry(self, since_tick: int | None = None) -> list[dict[str, Any]]:
        return list_telemetry_samples(self.conn, since_tick)

    def save_normalized_state(self, normalized_state: NormalizedNetworkState) -> str:
        return insert_normalized_state(self.conn, normalized_state)

    def get_normalized_state(self, state_id: str) -> dict[str, Any] | None:
        return get_normalized_state(self.conn, state_id)

    def get_observations(
        self,
        object_type: str | None = None,
        object_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return list_normalized_observations(self.conn, object_type, object_id)

    def save_snapshot(self, snapshot: MonitoringSnapshot) -> str:
        return insert_snapshot(self.conn, snapshot)

    def get_snapshot(self, snapshot_id_or_alias: str) -> dict[str, Any] | None:
        return get_snapshot(self.conn, snapshot_id_or_alias)

    def list_snapshots(self) -> list[dict[str, Any]]:
        return list_snapshots(self.conn)

    def list_alerts(self, since_tick: int | None = None) -> list[dict[str, Any]]:
        return list_alerts(self.conn, since_tick)

    def get_evidence(self, evidence_ref: EvidenceRef | dict[str, Any]) -> dict[str, Any] | None:
        ref = evidence_ref if isinstance(evidence_ref, EvidenceRef) else EvidenceRef.model_validate(evidence_ref)
        if ref.type == "event":
            return _find_by_id(self.get_recent_events(), ref.id)
        if ref.type == "telemetry":
            return _find_by_id(self.get_recent_telemetry(), ref.id)
        if ref.type == "link":
            return self.get_link(ref.id)
        if ref.type == "service":
            return self.get_service(ref.id)
        if ref.type == "snapshot":
            return self.get_snapshot(ref.id)
        if ref.type in {"observation", "device", "interface", "probe"}:
            observations = self.get_observations(object_id=ref.id)
            return observations[-1] if observations else None
        return None


def _find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None

