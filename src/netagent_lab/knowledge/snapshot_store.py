from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import get_snapshot, list_snapshots


def get_snapshot_by_id_or_alias(conn: sqlite3.Connection, snapshot_id_or_alias: str) -> dict[str, Any] | None:
    return get_snapshot(conn, snapshot_id_or_alias)


def get_snapshots(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return list_snapshots(conn)

