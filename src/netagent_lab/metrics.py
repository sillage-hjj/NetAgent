from __future__ import annotations

import sqlite3
from typing import Any


THRESHOLDS = {
    "cpu_utilization_percent": 85.0,
    "packet_loss_percent": 5.0,
}


def query_metric_trend(
    conn: sqlite3.Connection,
    device: str,
    metric: str,
    since: str | None = None,
) -> dict[str, Any]:
    if since:
        rows = conn.execute(
            """
            SELECT * FROM metrics
            WHERE device = ? AND metric = ? AND ts >= ?
            ORDER BY ts, id
            """,
            (device, metric, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM metrics WHERE device = ? AND metric = ? ORDER BY ts, id",
            (device, metric),
        ).fetchall()

    anomalous_samples = _anomalous_samples(rows)
    evidence = _metric_evidence(anomalous_samples or rows)
    threshold = THRESHOLDS.get(metric)
    if anomalous_samples:
        explanation = f"{device} has {metric} sample(s) above threshold {threshold}."
    elif rows:
        explanation = f"{device} has {metric} samples, none above the MVP threshold."
    else:
        explanation = f"No {metric} samples found for {device}."

    return {
        "anomalous": bool(anomalous_samples),
        "metric_samples": rows,
        "anomalous_samples": anomalous_samples,
        "evidence": evidence,
        "explanation": explanation,
    }


def find_anomalous_metrics_on_path(conn: sqlite3.Connection, path: list[str]) -> dict[str, Any]:
    if not path:
        return {
            "anomalous": False,
            "metric_samples": [],
            "anomalous_samples": [],
            "evidence": [],
            "explanation": "No path was supplied, so path metric correlation was not performed.",
        }

    placeholders = ",".join("?" for _ in path)
    rows = conn.execute(
        f"""
        SELECT * FROM metrics
        WHERE device IN ({placeholders})
        ORDER BY ts, id
        """,
        tuple(path),
    ).fetchall()
    anomalous_samples = _anomalous_samples(rows)
    evidence = _metric_evidence(anomalous_samples)

    if anomalous_samples:
        devices = sorted({sample["device"] for sample in anomalous_samples})
        explanation = f"Anomalous metrics found on path device(s): {', '.join(devices)}."
    else:
        explanation = "No metric samples on the inferred path exceeded MVP thresholds."

    return {
        "anomalous": bool(anomalous_samples),
        "metric_samples": rows,
        "anomalous_samples": anomalous_samples,
        "evidence": evidence,
        "explanation": explanation,
    }


def _anomalous_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        sample
        for sample in samples
        if sample["metric"] in THRESHOLDS and float(sample["value"]) > THRESHOLDS[sample["metric"]]
    ]


def _metric_evidence(samples: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "type": "metric",
            "id": sample["id"],
            "description": (
                f"{sample['device']} {sample['metric']}={sample['value']}"
                f"{' ' + sample['unit'] if sample.get('unit') else ''} at {sample['ts']}."
            ),
        }
        for sample in samples
    ]

