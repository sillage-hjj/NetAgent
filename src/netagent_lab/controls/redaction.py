from __future__ import annotations

from copy import deepcopy
from typing import Any


SENSITIVE_KEYS = ("management_ip", "secret", "token", "password", "community")


def redact_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    redacted = deepcopy(data)
    return _redact(redacted)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        for key in list(value):
            lowered = key.lower()
            if lowered == "management_ip" or any(fragment in lowered for fragment in SENSITIVE_KEYS[1:]):
                value.pop(key)
            else:
                value[key] = _redact(value[key])
    elif isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _redact(item)
    return value

