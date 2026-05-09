from netagent_lab.db import init_db
from netagent_lab.investigator import investigate_ticket
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.seed_loader import load_case


def test_investigator_identifies_acl_block_root_cause() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")
    parse_and_store_all(conn)

    result = investigate_ticket(conn, "T-001")

    assert result["root_cause_type"] == "acl_block"
    assert result["confidence"] == "high"
    assert result["impacted_path"]["reachable"] is True
    assert any(item["id"] == "ACL-DENY-ZRH-APPB-HTTPS" for item in result["evidence"])

