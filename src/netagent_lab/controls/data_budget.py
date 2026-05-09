from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_BUDGET = {
    "max_events": 50,
    "max_telemetry_samples": 100,
    "max_alerts": 20,
    "max_links": 100,
    "include_raw_payloads": False,
}


def apply_context_budget(context: dict[str, Any], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    effective = dict(DEFAULT_BUDGET)
    if budget:
        effective.update(budget)
    result = deepcopy(context)
    if isinstance(result.get("recent_events"), list):
        result["recent_events"] = result["recent_events"][: effective["max_events"]]
    if isinstance(result.get("recent_telemetry"), list):
        result["recent_telemetry"] = result["recent_telemetry"][: effective["max_telemetry_samples"]]
    if isinstance(result.get("active_alerts"), list):
        result["active_alerts"] = result["active_alerts"][: effective["max_alerts"]]
    links = result.get("link_state_metadata")
    if isinstance(links, dict):
        result["link_state_metadata"] = dict(list(links.items())[: effective["max_links"]])
    if not effective["include_raw_payloads"]:
        _drop_raw_payloads(result)
    result["budget"] = effective
    return result


def _drop_raw_payloads(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value):
            if key in {"raw_payload", "raw_payloads"}:
                value.pop(key)
            else:
                _drop_raw_payloads(value[key])
    elif isinstance(value, list):
        for item in value:
            _drop_raw_payloads(item)

