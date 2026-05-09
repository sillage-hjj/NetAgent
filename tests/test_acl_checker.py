from netfabric_mini.acl_checker import check_acl
from netfabric_mini.db import init_db
from netfabric_mini.seed_loader import load_case


PATH = ["client_zurich", "r1", "r2", "r3", "app_b"]


def test_acl_block_denies_zurich_https_to_app_b() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")

    result = check_acl(conn, "10.1.0.25", "10.2.0.10", "tcp", 443, PATH)

    assert result["result"] == "deny"
    assert result["matched_rule"]["rule_name"] == "BLOCK_ZURICH"
    assert result["matched_rule"]["id"] == "ACL-DENY-ZRH-APPB-HTTPS"
    assert "r3" in result["checked_devices"]
    assert any(item["id"] == "ACL-DENY-ZRH-APPB-HTTPS" for item in result["evidence"])


def test_performance_case_allows_zurich_https_to_app_b() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")

    result = check_acl(conn, "10.1.0.25", "10.2.0.10", "tcp", 443, PATH)

    assert result["result"] == "allow"
    assert result["matched_rule"]["rule_name"] == "ALLOW_ZURICH_HTTPS"


def test_protocol_and_port_must_match() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")

    udp_result = check_acl(conn, "10.1.0.25", "10.2.0.10", "udp", 443, PATH)
    ssh_result = check_acl(conn, "10.1.0.25", "10.2.0.10", "tcp", 22, PATH)

    assert udp_result["result"] == "allow"
    assert udp_result["matched_rule"] is None
    assert ssh_result["result"] == "allow"
    assert ssh_result["matched_rule"] is None


def test_non_matching_prefix_does_not_trigger_rule() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")

    result = check_acl(conn, "10.9.0.25", "10.2.0.10", "tcp", 443, PATH)

    assert result["result"] == "allow"
    assert result["matched_rule"]["rule_name"] == "ALLOW_OTHER_APPB_HTTPS"

