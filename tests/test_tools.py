import inspect
import json

from netfabric_mini import tools
from netfabric_mini.db import init_db
from netfabric_mini.log_parser import parse_and_store_all
from netfabric_mini.seed_loader import load_case
from netfabric_mini.tools import (
    check_acl_tool,
    get_raw_log,
    get_recent_events,
    get_ticket,
    infer_path_tool,
    query_metric_trend_tool,
)


def test_tools_return_json_serializable_objects_with_standard_shape() -> None:
    conn = init_db(":memory:")
    load_case(conn, "performance_degradation")
    parse_and_store_all(conn)
    path = ["client_zurich", "r1", "r2", "r3", "app_b"]

    results = [
        get_ticket(conn, "T-001"),
        get_recent_events(conn),
        get_raw_log(conn, "rawlog-0001"),
        infer_path_tool(conn, "client_zurich", "app_b"),
        check_acl_tool(conn, "10.1.0.25", "10.2.0.10", "tcp", 443, path),
        query_metric_trend_tool(conn, "r2", "cpu_utilization_percent"),
    ]

    for result in results:
        assert set(result) == {"tool_name", "ok", "result", "evidence", "errors"}
        assert result["ok"] is True
        assert result["evidence"]
        json.dumps(result)


def test_tool_not_found_errors_are_structured() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")

    result = get_ticket(conn, "missing")

    assert result["ok"] is False
    assert result["errors"] == ["Ticket not found: missing"]
    json.dumps(result)


def test_tools_module_does_not_expose_database_mutation_helpers() -> None:
    public_names = {name for name in dir(tools) if not name.startswith("_")}

    assert "insert_device" not in public_names
    assert "insert_event" not in public_names
    assert "reset_case_tables" not in public_names


def test_tools_do_not_import_external_command_execution_modules() -> None:
    source = inspect.getsource(tools)

    assert "subprocess" not in source
    assert "os.system" not in source
    assert "paramiko" not in source
