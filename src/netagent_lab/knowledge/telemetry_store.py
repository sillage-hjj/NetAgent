from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import list_telemetry_samples


def get_recent_telemetry(conn: sqlite3.Connection, since_tick: int | None = None) -> list[dict[str, Any]]:
    return list_telemetry_samples(conn, since_tick)

