from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from netfabric_mini.normalization.schemas import EvidenceRef


class CollectorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collector: str
    source: str
    ok: bool
    tick: int = Field(ge=0)
    result: dict[str, Any] | list[Any]
    evidence: list[EvidenceRef] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

