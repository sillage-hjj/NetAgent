from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceRef(NormalizedModel):
    type: str
    id: str
    description: str | None = None


class NormalizedObservation(NormalizedModel):
    id: str
    source: str
    observed_at_tick: int = Field(ge=0)
    object_type: str
    object_id: str
    attributes: dict[str, Any]
    evidence: list[EvidenceRef] = Field(default_factory=list)


class NormalizedInventory(NormalizedModel):
    devices: dict[str, Any] = Field(default_factory=dict)
    interfaces: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)
    probes: dict[str, Any] = Field(default_factory=dict)


class NormalizedNetworkState(NormalizedModel):
    id: str
    tick: int = Field(ge=0)
    inventory: NormalizedInventory
    observations: list[NormalizedObservation] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)

