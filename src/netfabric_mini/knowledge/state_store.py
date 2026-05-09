from __future__ import annotations

import sqlite3

from netfabric_mini.sim.state import SimulationStateStore


def get_state(conn: sqlite3.Connection) -> SimulationStateStore:
    return SimulationStateStore.load(conn)

