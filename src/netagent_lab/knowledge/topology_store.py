from __future__ import annotations

import sqlite3

from netagent_lab.db import load_topology_from_db
from netagent_lab.sim.schemas import SimTopology


def get_topology(conn: sqlite3.Connection) -> SimTopology:
    return load_topology_from_db(conn)

