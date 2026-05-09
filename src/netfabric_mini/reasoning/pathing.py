from __future__ import annotations

from typing import Any

from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.sim.pathing import build_available_graph as _build_graph
from netfabric_mini.sim.pathing import infer_simulated_path


def build_available_graph(kb: KnowledgeBase):
    return _build_graph(kb.get_current_state())


def infer_path(kb: KnowledgeBase, src_device: str, dst_device: str) -> dict[str, Any]:
    result = infer_simulated_path(kb.get_current_state(), src_device, dst_device)
    result.setdefault("evidence", [])
    return result

