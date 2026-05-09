from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


State = Literal["up", "down"]
ServiceStatus = Literal["up", "down", "degraded"]
Severity = Literal["info", "warning", "critical"]


class SimModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SimSite(SimModel):
    id: str
    name: str
    region: str | None = None


class SimInterface(SimModel):
    id: str
    name: str
    type: str = "ethernet"
    admin_state: State = "up"
    oper_state: State = "up"
    speed_mbps: int | None = Field(default=None, gt=0)
    ip: str | None = None
    description: str | None = None


class SimDevice(SimModel):
    id: str
    hostname: str
    role: str
    site: str | None = None
    vendor: str | None = None
    model: str | None = None
    management_ip: str | None = None
    interfaces: list[SimInterface]


class SimEndpoint(SimModel):
    device: str
    interface: str


class SimLink(SimModel):
    id: str
    endpoint_a: SimEndpoint
    endpoint_b: SimEndpoint
    weight: int = Field(default=1, ge=1)
    admin_state: State = "up"
    oper_state: State = "up"
    bandwidth_mbps: int = Field(gt=0)
    latency_ms: float = Field(default=1.0, ge=0)
    jitter_ms: float = Field(default=0.0, ge=0)
    loss_percent: float = Field(default=0.0, ge=0, le=100)
    utilization_percent: float = Field(default=0.0, ge=0, le=100)
    error_rate_percent: float = Field(default=0.0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)


class SimService(SimModel):
    id: str
    name: str
    device: str
    ip: str
    protocol: str
    port: int = Field(ge=1, le=65535)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"


class SimProbe(SimModel):
    id: str
    name: str
    source_device: str
    target_service: str
    protocol: str
    port: int = Field(ge=1, le=65535)
    interval_ticks: int = Field(default=1, ge=1)
    enabled: bool = True


class SimTopology(SimModel):
    name: str
    description: str | None = None
    version: str
    sites: list[SimSite]
    devices: list[SimDevice]
    links: list[SimLink]
    services: list[SimService]
    probes: list[SimProbe] = Field(default_factory=list)


class SimulationMetadata(SimModel):
    topology_name: str
    current_tick: int = Field(ge=0)
    random_seed: int | None = None
    created_at: str
    updated_at: str


class DeviceRuntimeState(SimModel):
    device_id: str
    admin_state: State
    oper_state: State
    cpu_utilization_percent: float = Field(ge=0, le=100)
    memory_utilization_percent: float = Field(ge=0, le=100)
    last_change_tick: int = Field(ge=0)
    last_event_id: str | None = None


class InterfaceRuntimeState(SimModel):
    device_id: str
    interface_id: str
    admin_state: State
    oper_state: State
    rx_errors: int = Field(ge=0)
    tx_errors: int = Field(ge=0)
    utilization_percent: float = Field(ge=0, le=100)
    last_change_tick: int = Field(ge=0)
    last_event_id: str | None = None


class LinkRuntimeState(SimModel):
    link_id: str
    admin_state: State
    oper_state: State
    bandwidth_mbps: int = Field(gt=0)
    latency_ms: float = Field(ge=0)
    jitter_ms: float = Field(ge=0)
    loss_percent: float = Field(ge=0, le=100)
    utilization_percent: float = Field(ge=0, le=100)
    error_rate_percent: float = Field(ge=0, le=100)
    flap_count: int = Field(ge=0)
    last_change_tick: int = Field(ge=0)
    last_event_id: str | None = None
    failure_reason: str | None = None


class ServiceRuntimeState(SimModel):
    service_id: str
    status: ServiceStatus
    latency_ms: float | None = Field(default=None, ge=0)
    loss_percent: float | None = Field(default=None, ge=0, le=100)
    last_change_tick: int = Field(ge=0)
    last_event_id: str | None = None


class SimulationEvent(SimModel):
    id: str
    tick: int = Field(ge=0)
    ts: str
    event_type: str
    target_type: str
    target_id: str
    severity: Severity
    params: dict[str, Any]
    description: str


class TelemetrySample(SimModel):
    id: str
    tick: int = Field(ge=0)
    ts: str
    source: str
    metric: str
    target_type: str
    target_id: str
    value: float
    unit: str | None = None
    labels: dict[str, Any] = Field(default_factory=dict)


class MonitoringSnapshot(SimModel):
    id: str
    tick: int = Field(ge=0)
    ts: str
    topology_name: str
    inventory: dict[str, Any]
    devices: dict[str, Any]
    interfaces: dict[str, Any]
    links: dict[str, Any]
    services: dict[str, Any]
    probes: dict[str, Any]
    paths: dict[str, Any]
    alerts: list[dict[str, Any]]
    events_since_previous: list[dict[str, Any]]

