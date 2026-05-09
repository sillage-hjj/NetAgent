from __future__ import annotations

from typing import Any

from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.monitoring.diff import diff_snapshots as _diff_snapshots


def diff_snapshots(snapshot_a: dict[str, Any], snapshot_b: dict[str, Any]) -> dict[str, Any]:
    result = _diff_snapshots(snapshot_a, snapshot_b)
    result["evidence"] = [
        {"type": "snapshot", "id": snapshot_a["id"], "description": "Diff source snapshot."},
        {"type": "snapshot", "id": snapshot_b["id"], "description": "Diff target snapshot."},
    ]
    return result


def diff_latest_snapshots(kb: KnowledgeBase) -> dict[str, Any]:
    before = kb.get_snapshot("latest-1")
    after = kb.get_snapshot("latest")
    if before is None or after is None:
        raise ValueError("At least two snapshots are required")
    return diff_snapshots(before, after)

