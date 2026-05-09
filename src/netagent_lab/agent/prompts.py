from __future__ import annotations

import json
from typing import Any


def build_system_prompt(config: Any) -> str:
    return (
        "You are a read-only network operations investigation agent for a simulated network observability system.\n"
        "You must use tools for network facts. Never invent topology, telemetry, path, reachability, alerts, or logs.\n"
        "Never claim that a remediation was executed. Never directly mutate simulated state.\n"
        "Cite evidence IDs for all major claims. Prefer deterministic tools for path inference, reachability, health, alerts, diffs, and snapshots.\n"
        "If evidence is missing, say what evidence is missing. Keep explanations concise and operational.\n"
        "Separate observations from hypotheses. Separate read-only next checks from remediation suggestions.\n"
        "Mark remediation as requiring human approval. Respect context budget and redaction.\n"
        f"Provider={getattr(config, 'provider', 'unknown')} Require evidence={getattr(config, 'require_evidence', True)}."
    )


def build_user_prompt(question: str, context_summary: dict | str) -> str:
    if isinstance(context_summary, dict):
        context_text = json.dumps(context_summary, sort_keys=True)
    else:
        context_text = context_summary
    return f"User question:\n{question}\n\nBudgeted context summary:\n{context_text}"


def build_repair_prompt(validation_errors: list[str], previous_report: dict) -> str:
    return (
        "The previous structured report failed validation. Repair it without adding unsupported facts.\n"
        f"Validation errors: {validation_errors}\n"
        f"Previous report: {json.dumps(previous_report, sort_keys=True)}"
    )

