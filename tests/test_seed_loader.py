from pathlib import Path

import pytest

from netagent_lab.db import count_rows, init_db, query_all
from netagent_lab.seed_loader import load_case


EXPECTED_COUNTS = {
    "link_down": {
        "devices": 5,
        "links": 4,
        "raw_logs": 3,
        "acl_rules": 1,
        "tickets": 1,
        "metrics": 2,
    },
    "acl_block": {
        "devices": 5,
        "links": 4,
        "raw_logs": 2,
        "acl_rules": 2,
        "tickets": 1,
        "metrics": 2,
    },
    "performance_degradation": {
        "devices": 5,
        "links": 4,
        "raw_logs": 2,
        "acl_rules": 1,
        "tickets": 1,
        "metrics": 3,
    },
}


@pytest.mark.parametrize("case_name", sorted(EXPECTED_COUNTS))
def test_load_case_inserts_expected_rows(case_name: str) -> None:
    conn = init_db(":memory:")

    summary = load_case(conn, case_name)

    assert summary["case_name"] == case_name
    for table, expected_count in EXPECTED_COUNTS[case_name].items():
        assert count_rows(conn, table) == expected_count


def test_raw_log_ids_are_stable() -> None:
    conn = init_db(":memory:")

    load_case(conn, "acl_block")

    raw_logs = query_all(conn, "raw_logs")
    assert [row["id"] for row in raw_logs] == ["rawlog-0001", "rawlog-0002"]


def test_missing_case_fails_clearly() -> None:
    conn = init_db(":memory:")

    with pytest.raises(FileNotFoundError, match="Case directory not found"):
        load_case(conn, "does_not_exist")


def test_malformed_case_fails_clearly(tmp_path: Path) -> None:
    case_dir = tmp_path / "bad_case"
    case_dir.mkdir()
    (case_dir / "topology.yaml").write_text("devices: []\nlinks: []\n", encoding="utf-8")

    conn = init_db(":memory:")
    with pytest.raises(ValueError, match="missing required file"):
        load_case(conn, "bad_case", cases_dir=tmp_path)

