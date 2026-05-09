from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Device(StrictModel):
    id: str
    role: str
    site: str | None = None
    vendor: str | None = None


class Link(StrictModel):
    src_device: str
    src_interface: str
    dst_device: str
    dst_interface: str
    weight: int = Field(ge=1)
    status: Literal["up", "down"]


class AclRule(StrictModel):
    id: str
    device: str
    rule_name: str
    src_prefix: str
    dst_prefix: str
    protocol: str
    port: int = Field(ge=1, le=65535)
    action: Literal["allow", "deny"]


class Ticket(StrictModel):
    id: str
    ts: str
    text: str
    src_site: str | None = None
    dst_service: str | None = None
    protocol: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)


class MetricSample(StrictModel):
    id: str
    ts: str
    device: str
    metric: str
    value: float
    unit: str | None = None


class ParsedEvent(StrictModel):
    id: str
    ts: str
    device: str
    event_type: str
    severity: str
    params: dict[str, Any]
    raw_log_id: str


class RawLog(StrictModel):
    id: str
    line: str


class TopologyFile(StrictModel):
    devices: list[Device]
    links: list[Link]


class AclRulesFile(StrictModel):
    acl_rules: list[AclRule]


class MetricsFile(StrictModel):
    metrics: list[MetricSample]


class TicketsFile(StrictModel):
    tickets: list[Ticket]

