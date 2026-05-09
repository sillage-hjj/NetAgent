from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.agent_tools._common import ok_result
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.reasoning.diff import diff_latest_snapshots as _diff_latest


def list_snapshots(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("list_snapshots", {"snapshots": KnowledgeBase.from_db(conn).list_snapshots()})


def diff_latest_snapshots(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("diff_latest_snapshots", _diff_latest(KnowledgeBase.from_db(conn)))

