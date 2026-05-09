from __future__ import annotations

import sqlite3

from netagent_lab.sim.state import SimulationStateStore


def get_state(conn: sqlite3.Connection) -> SimulationStateStore:
    return SimulationStateStore.load(conn)

