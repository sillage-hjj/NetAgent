from __future__ import annotations

from netagent_lab.agent.run_store import complete_run, create_run, get_run, list_runs, list_tool_calls, record_tool_call
from netagent_lab.agent.session_store import append_message, create_session, list_messages
from netagent_lab.db import init_sim_db
from netagent_lab.llm.client_protocol import LLMToolCall
from netagent_lab.agent.tool_contracts import make_tool_result


def test_sessions_runs_and_tool_calls_persist() -> None:
    conn = init_sim_db(":memory:")
    session_id = create_session(conn, "test")
    append_message(conn, session_id, "user", "hello")
    run_id = create_run(conn, session_id, "question", "mock", None)
    result = make_tool_result(tool_name="get_current_context", ok=True, trace_id="trace-1", result={}, read_only=True)
    record_tool_call(conn, run_id, LLMToolCall(id="tc-1", name="get_current_context", arguments={}), result)
    complete_run(conn, run_id, {"summary": "ok", "password": "secret"}, {"tokens": 1})

    assert list_messages(conn, session_id)
    assert get_run(conn, run_id)["final_report"]["summary"] == "ok"
    assert "password" not in get_run(conn, run_id)["final_report"]
    assert list_runs(conn)
    assert list_tool_calls(conn, run_id)[0]["trace_id"] == "trace-1"

