from __future__ import annotations

import json
import sqlite3
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from netagent_lab.agent.schemas import AgentReport
from netagent_lab.controls.evidence import collect_evidence_refs
from netagent_lab.db import list_alerts, list_sim_events, list_snapshots, list_telemetry_samples
from netagent_lab.evals.expected_evidence import ExpectedEvidenceSpec, get_expected_evidence_spec
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.normalization.schemas import EvidenceRef
from netagent_lab.sim.state import SimulationStateStore


PASS_THRESHOLD = 0.70


class EvidenceRelevanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    evidence_existence_score: float
    evidence_relevance_score: float
    evidence_specificity_score: float
    evidence_recency_score: float
    causal_alignment_score: float
    irrelevant_evidence_count: int
    missing_expected_evidence: list[str] = Field(default_factory=list)
    unsupported_or_unknown_evidence: list[str] = Field(default_factory=list)
    overall_grounding_score: float
    passed: bool


def evaluate_evidence_relevance(
    report: AgentReport,
    scenario_name: str,
    conn: sqlite3.Connection | None = None,
) -> EvidenceRelevanceResult:
    spec = get_expected_evidence_spec(scenario_name)
    refs = collect_evidence_refs(report.model_dump(mode="json"))
    if spec is None:
        exists = 1.0 if refs else 0.0
        return EvidenceRelevanceResult(
            scenario_name=scenario_name,
            evidence_existence_score=exists,
            evidence_relevance_score=exists,
            evidence_specificity_score=exists,
            evidence_recency_score=exists,
            causal_alignment_score=exists,
            irrelevant_evidence_count=0,
            overall_grounding_score=exists,
            passed=bool(refs),
        )

    resolved = [_resolve_evidence(conn, ref) if conn is not None else None for ref in refs]
    existence_score = _existence_score(refs, resolved, conn is not None)
    relevant_refs = [
        ref for ref, target in zip(refs, resolved)
        if _is_relevant(ref, target, spec)
    ]
    relevance_score = min(1.0, len(_matched_required_types(refs, resolved, spec)) / max(1, len(_minimum_required_types(spec))))
    specificity_score = _specificity_score(refs, resolved, spec)
    recency_score = _recency_score(refs, resolved)
    causal_score = _causal_alignment_score(refs, resolved, spec)
    irrelevant = [
        ref for ref, target in zip(refs, resolved)
        if not _is_relevant(ref, target, spec) and ref.type not in {"context", "ticket"}
    ]
    missing = [
        evidence_type for evidence_type in _minimum_required_types(spec)
        if evidence_type not in _matched_required_types(refs, resolved, spec)
    ]
    unsupported = [
        f"{ref.type}:{ref.id}"
        for ref, target in zip(refs, resolved)
        if conn is not None and target is None and ref.type not in {"context"}
    ]
    generic_only = bool(refs) and all(ref.type in {"context", "ticket"} for ref in refs)
    irrelevant_penalty = min(0.25, max(0, len(irrelevant) - spec.max_irrelevant_refs) * 0.05)
    overall = max(
        0.0,
        round(
            0.20 * existence_score
            + 0.25 * relevance_score
            + 0.20 * specificity_score
            + 0.15 * recency_score
            + 0.20 * causal_score
            - irrelevant_penalty,
            3,
        ),
    )
    passed = overall >= PASS_THRESHOLD and not generic_only and not missing
    return EvidenceRelevanceResult(
        scenario_name=scenario_name,
        evidence_existence_score=round(existence_score, 3),
        evidence_relevance_score=round(relevance_score, 3),
        evidence_specificity_score=round(specificity_score, 3),
        evidence_recency_score=round(recency_score, 3),
        causal_alignment_score=round(causal_score, 3),
        irrelevant_evidence_count=len(irrelevant),
        missing_expected_evidence=missing,
        unsupported_or_unknown_evidence=unsupported,
        overall_grounding_score=overall,
        passed=passed,
    )


def _minimum_required_types(spec: ExpectedEvidenceSpec) -> list[str]:
    if spec.scenario_name == "link_failure":
        return ["event", "link"]
    if spec.scenario_name == "congestion":
        return ["link", "probe"]
    if spec.scenario_name == "route_withdrawal":
        return ["event", "link"]
    return spec.required_evidence_types[:2]


def _matched_required_types(
    refs: list[EvidenceRef],
    resolved: list[dict[str, Any] | None],
    spec: ExpectedEvidenceSpec,
) -> set[str]:
    matched: set[str] = set()
    for ref, target in zip(refs, resolved):
        if ref.type in spec.required_evidence_types and _is_relevant(ref, target, spec):
            matched.add(ref.type)
        if ref.type == "event" and _target_text(ref, target).find("route_withdrawal") >= 0:
            matched.add("route_block")
        if ref.type == "probe" and _target_text(ref, target).find("degraded") >= 0:
            matched.add("probe")
    return matched


def _existence_score(refs: list[EvidenceRef], resolved: list[dict[str, Any] | None], checked: bool) -> float:
    if not refs:
        return 0.0
    if not checked:
        return 1.0
    return sum(target is not None for target in resolved) / len(refs)


def _specificity_score(
    refs: list[EvidenceRef],
    resolved: list[dict[str, Any] | None],
    spec: ExpectedEvidenceSpec,
) -> float:
    if not refs:
        return 0.0
    preferred = set(spec.preferred_object_ids)
    hits = 0
    for ref, target in zip(refs, resolved):
        text = _target_text(ref, target)
        if ref.id in preferred or any(object_id in text for object_id in preferred):
            hits += 1
    return hits / len(refs)


def _recency_score(refs: list[EvidenceRef], resolved: list[dict[str, Any] | None]) -> float:
    tick_values = []
    for ref, target in zip(refs, resolved):
        tick = _extract_tick(ref, target)
        if tick is not None:
            tick_values.append(tick)
    if not tick_values:
        return 0.7 if refs else 0.0
    latest = max(tick_values)
    if latest == 0:
        return 1.0
    recent = sum(tick >= latest - 1 for tick in tick_values)
    return recent / len(tick_values)


def _causal_alignment_score(
    refs: list[EvidenceRef],
    resolved: list[dict[str, Any] | None],
    spec: ExpectedEvidenceSpec,
) -> float:
    if not refs:
        return 0.0
    hits = sum(_causal_hit(ref, target, spec) for ref, target in zip(refs, resolved))
    return hits / len(refs)


def _is_relevant(ref: EvidenceRef, target: dict[str, Any] | None, spec: ExpectedEvidenceSpec) -> bool:
    text = _target_text(ref, target)
    if ref.type in spec.required_evidence_types and _causal_hit(ref, target, spec):
        return True
    if ref.id in spec.preferred_object_ids:
        return True
    return any(object_id in text for object_id in spec.preferred_object_ids)


def _causal_hit(ref: EvidenceRef, target: dict[str, Any] | None, spec: ExpectedEvidenceSpec) -> bool:
    text = _target_text(ref, target)
    if spec.scenario_name == "link_failure":
        return ref.type in {"link", "path_result", "probe"} or any(token in text for token in ("link_down", "fiber", "link_r1_r2", "failover"))
    if spec.scenario_name == "congestion":
        return any(token in text for token in ("high_latency", "high_packet_loss", "high_utilization", "loss", "latency", "utilization", "degraded", "link_r1_r2"))
    if spec.scenario_name == "route_withdrawal":
        return ref.type in {"link", "probe", "path_result", "service"} or any(token in text for token in ("route_withdrawal", "route_block", "routeblock-1", "unreachable", "bgp_withdrawal"))
    if spec.scenario_name == "acl_block":
        return any(token in text for token in ("acl", "deny", "block_zurich", "acl-deny"))
    return ref.type in spec.required_evidence_types


def _target_text(ref: EvidenceRef, target: dict[str, Any] | None) -> str:
    return f"{ref.model_dump(mode='json')} {json.dumps(target or {}, sort_keys=True)}".lower()


def _extract_tick(ref: EvidenceRef, target: dict[str, Any] | None) -> int | None:
    if target and isinstance(target.get("tick"), int):
        return int(target["tick"])
    for marker in ("tick-", "event-"):
        if marker in ref.id:
            tail = ref.id.split(marker, 1)[1].split("-", 1)[0]
            try:
                return int(tail)
            except ValueError:
                return None
    return None


def _resolve_evidence(conn: sqlite3.Connection | None, ref: EvidenceRef) -> dict[str, Any] | None:
    if conn is None:
        return None
    kb = KnowledgeBase.from_db(conn)
    if ref.type in {"event", "telemetry", "link", "service", "snapshot", "observation", "device", "interface", "probe"}:
        return kb.get_evidence(ref)
    if ref.type == "alert":
        return _find_by_id(list_alerts(conn), ref.id)
    if ref.type == "route_block":
        return _find_by_id(SimulationStateStore.load(conn).route_blocks, ref.id)
    if ref.type == "path_result":
        return _find_path_result(conn, ref.id)
    if ref.type == "topology":
        topology = kb.get_topology().model_dump(mode="json")
        return topology if topology.get("name") == ref.id else None
    if ref.type == "context":
        return {"id": ref.id, "type": "context"}
    return None


def _find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def _find_path_result(conn: sqlite3.Connection, evidence_id: str) -> dict[str, Any] | None:
    for snapshot in list_snapshots(conn):
        found = _find_nested_path(snapshot.get("paths"), evidence_id)
        if found is not None:
            return found
    return None


def _find_nested_path(value: Any, evidence_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        for evidence in value.get("evidence", []) if isinstance(value.get("evidence"), list) else []:
            if isinstance(evidence, dict) and evidence.get("id") == evidence_id:
                return value
        for child in value.values():
            found = _find_nested_path(child, evidence_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_nested_path(child, evidence_id)
            if found is not None:
                return found
    return None
