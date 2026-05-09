from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.db import list_sim_events


def get_recent_events(conn: sqlite3.Connection, since_tick: int | None = None) -> list[dict[str, Any]]:
    return list_sim_events(conn, since_tick)

