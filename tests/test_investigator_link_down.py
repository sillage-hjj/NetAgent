from netagent_lab.db import init_db
from netagent_lab.investigator import investigate_ticket
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.seed_loader import load_case


def test_investigator_identifies_link_down_root_cause() -> None:
    conn = init_db(":memory:")
    load_case(conn, "link_down")
    parse_and_store_all(conn)

    result = investigate_ticket(conn, "T-001")

    assert result["root_cause_type"] == "link_down"
    assert result["confidence"] in {"medium", "high"}
    assert any(
        item["type"] == "event" and ("link_state_change" in item["description"] or "routing_neighbor_change" in item["description"])
        for item in result["evidence"]
    )
    assert any(trace["tool_name"] == "infer_path" for trace in result["tool_trace"])

