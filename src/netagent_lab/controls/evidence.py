from __future__ import annotations

from typing import Any

from netagent_lab.normalization.schemas import EvidenceRef


def make_evidence_ref(type: str, id: str, description: str | None = None) -> EvidenceRef:
    return EvidenceRef(type=type, id=id, description=description)


def collect_evidence_refs(result: dict[str, Any]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    _walk(result, refs)
    seen: set[tuple[str, str]] = set()
    unique: list[EvidenceRef] = []
    for ref in refs:
        key = (ref.type, ref.id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def validate_evidence_refs(result: dict[str, Any]) -> bool:
    if "evidence" in result and not result["evidence"]:
        return False
    for key in ("alerts", "reasoning_results"):
        items = result.get(key)
        if isinstance(items, list) and any(isinstance(item, dict) and not item.get("evidence") for item in items):
            return False
    return bool(collect_evidence_refs(result))


def _walk(value: Any, refs: list[EvidenceRef]) -> None:
    if isinstance(value, dict):
        if {"type", "id"} <= set(value) and isinstance(value.get("type"), str) and isinstance(value.get("id"), str):
            refs.append(EvidenceRef(type=value["type"], id=value["id"], description=value.get("description")))
        for child in value.values():
            _walk(child, refs)
    elif isinstance(value, list):
        for child in value:
            _walk(child, refs)

