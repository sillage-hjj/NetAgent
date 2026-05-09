from netfabric_mini.db import count_rows, init_db, query_all
from netfabric_mini.log_parser import parse_and_store_all, parse_log_line
from netfabric_mini.seed_loader import load_case


def test_parse_link_state_change() -> None:
    event = parse_log_line(
        "rawlog-0001",
        "2026-05-01T10:01:12Z r2 %LINK-3-UPDOWN: Interface eth1 changed state to down",
    )

    assert event is not None
    assert event.event_type == "link_state_change"
    assert event.raw_log_id == "rawlog-0001"
    assert event.params == {"interface": "eth1", "state": "down"}


def test_parse_routing_neighbor_change() -> None:
    event = parse_log_line(
        "rawlog-0002",
        "2026-05-01T10:01:15Z r1 %OSPF-5-ADJCHG: Neighbor 10.0.12.2 on eth1 from FULL to DOWN",
    )

    assert event is not None
    assert event.event_type == "routing_neighbor_change"
    assert event.params == {
        "protocol": "OSPF",
        "neighbor": "10.0.12.2",
        "interface": "eth1",
        "from_state": "FULL",
        "to_state": "DOWN",
    }


def test_parse_acl_deny() -> None:
    event = parse_log_line(
        "rawlog-0003",
        "2026-05-01T10:02:03Z r3 %ACL-4-DENY: tcp 10.1.0.25:52344 -> 10.2.0.10:443 denied by BLOCK_ZURICH",
    )

    assert event is not None
    assert event.event_type == "acl_deny"
    assert event.params["src_ip"] == "10.1.0.25"
    assert event.params["src_port"] == 52344
    assert event.params["dst_ip"] == "10.2.0.10"
    assert event.params["dst_port"] == 443
    assert event.params["acl_name"] == "BLOCK_ZURICH"


def test_parse_cpu_high() -> None:
    event = parse_log_line(
        "rawlog-0004",
        "2026-05-01T10:03:10Z r2 %CPU-5-HIGH: CPU utilization 94 percent for 300 seconds",
    )

    assert event is not None
    assert event.event_type == "cpu_high"
    assert event.params == {"utilization_percent": 94, "duration_seconds": 300}


def test_parse_packet_loss() -> None:
    event = parse_log_line(
        "rawlog-0005",
        "2026-05-01T10:04:10Z r2 %SLA-4-LOSS: Packet loss to 10.2.0.10 is 18 percent over 300 seconds",
    )

    assert event is not None
    assert event.event_type == "packet_loss"
    assert event.params == {"target_ip": "10.2.0.10", "loss_percent": 18, "duration_seconds": 300}


def test_unknown_or_incomplete_lines_return_none() -> None:
    assert parse_log_line("rawlog-0099", "noise without known structure") is None
    assert (
        parse_log_line(
            "rawlog-0100",
            "2026-05-01T10:01:12Z r2 %LINK-3-UPDOWN: Interface eth1 changed state",
        )
        is None
    )


def test_parse_and_store_all_preserves_raw_log_ids() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")

    summary = parse_and_store_all(conn)

    assert summary["parsed_events"] == 2
    assert count_rows(conn, "events") == 2
    events = query_all(conn, "events")
    assert [event["raw_log_id"] for event in events] == ["rawlog-0001", "rawlog-0002"]

