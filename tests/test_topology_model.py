import pytest

from netfabric_mini.db import init_db
from netfabric_mini.seed_loader import load_case
from netfabric_mini.topology_model import build_graph, infer_path


@pytest.mark.parametrize(
    ("case_name", "reachable"),
    [
        ("link_down", False),
        ("acl_block", True),
        ("performance_degradation", True),
    ],
)
def test_infer_path_reachability_by_case(case_name: str, reachable: bool) -> None:
    conn = init_db(":memory:")
    load_case(conn, case_name)

    result = infer_path(conn, "client_zurich", "app_b")

    assert result["reachable"] is reachable
    assert result["src_device"] == "client_zurich"
    assert result["dst_device"] == "app_b"
    assert result["evidence"]


def test_link_down_path_includes_down_link_evidence() -> None:
    conn = init_db(":memory:")
    load_case(conn, "link_down")

    result = infer_path(conn, "client_zurich", "app_b")

    assert result["reachable"] is False
    assert result["path"] == []
    assert any(link["status"] == "down" for link in result["down_links"])
    assert any(item["type"] == "link" and item["id"] == "link-0003" for item in result["evidence"])


def test_reachable_path_contains_ordered_links() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")

    result = infer_path(conn, "client_zurich", "app_b")

    assert result["path"] == ["client_zurich", "r1", "r2", "r3", "app_b"]
    assert [link["id"] for link in result["path_links"]] == [
        "link-0001",
        "link-0002",
        "link-0003",
        "link-0004",
    ]


def test_build_graph_uses_only_up_links() -> None:
    conn = init_db(":memory:")
    load_case(conn, "link_down")

    graph = build_graph(conn)

    assert graph.has_node("client_zurich")
    assert not graph.has_edge("r2", "r3")

