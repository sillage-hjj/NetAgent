from netagent_lab.db import init_db
from netagent_lab.investigator import investigate_ticket
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.seed_loader import load_case


def test_investigator_identifies_performance_degradation() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")
    parse_and_store_all(conn)

    result = investigate_ticket(conn, "T-001")

    assert result["root_cause_type"] == "performance_degradation"
    assert result["confidence"] in {"medium", "high"}
    assert any(
        item["type"] in {"metric", "event"} and ("r2" in item["description"] or item["id"].startswith("MET-PD-R2"))
        for item in result["evidence"]
    )

