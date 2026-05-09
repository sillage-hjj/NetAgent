from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MonitoringJob(OrchestrationModel):
    id: str
    created_tick: int = Field(ge=0)
    status: Literal["created", "running", "completed", "failed"]
    focus: dict[str, Any] | None = None


class MonitoringCycleResult(OrchestrationModel):
    job_id: str
    tick: int
    collector_results: list[dict[str, Any]]
    normalized_state_id: str | None = None
    reasoning_results: dict[str, Any]
    alerts: list[dict[str, Any]]
    snapshot_id: str
    export_refs: dict[str, Any]
    errors: list[str] = Field(default_factory=list)

