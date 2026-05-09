from __future__ import annotations

import sqlite3
from typing import Protocol

from netagent_lab.investigator import investigate_ticket


class ToolCallingAgentAdapter(Protocol):
    """Interface for a future planner/summarizer constrained by deterministic tools."""

    def investigate(self, conn: sqlite3.Connection, ticket_id: str) -> dict:
        """Return an evidence-grounded investigation result."""
        ...


class MockLLMAdapter:
    """Offline adapter that delegates to the deterministic rule-based investigator."""

    def investigate(self, conn: sqlite3.Connection, ticket_id: str) -> dict:
        return investigate_ticket(conn, ticket_id)

