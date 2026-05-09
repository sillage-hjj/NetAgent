from netagent_lab.db import init_db
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.metrics import find_anomalous_metrics_on_path, query_metric_trend
from netagent_lab.seed_loader import load_case
from netagent_lab.tools import find_relevant_events_on_path
from netagent_lab.topology_model import infer_path


def test_performance_case_finds_metric_anomaly_on_path() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")
    path = infer_path(conn, "client_zurich", "app_b")["path"]

    result = find_anomalous_metrics_on_path(conn, path)

    assert result["anomalous"] is True
    assert any(sample["id"] == "MET-PD-R2-CPU-1003" for sample in result["metric_samples"])
    assert any(item["id"] == "MET-PD-R2-LOSS-1004" for item in result["evidence"])


def test_metric_trend_applies_threshold() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")

    result = query_metric_trend(conn, "r2", "cpu_utilization_percent")

    assert result["anomalous"] is True
    assert result["metric_samples"][0]["id"] == "MET-PD-R2-CPU-1003"


def test_link_down_case_finds_link_and_routing_events() -> None:
    conn = init_db(":memory:")
    load_case(conn, "link_down")
    parse_and_store_all(conn)

    result = find_relevant_events_on_path(conn, ["client_zurich", "r1", "r2", "r3", "app_b"])

    assert result["relevant"] is True
    assert any(event["event_type"] == "link_state_change" for event in result["events"])
    assert any(event["event_type"] == "routing_neighbor_change" for event in result["events"])
    assert all(item["id"].startswith("event-") for item in result["evidence"])

