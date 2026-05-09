from __future__ import annotations

import argparse
from pathlib import Path

from netfabric_mini.ui import data_access
from netfabric_mini.ui.components import render_json_expander, render_table
from netfabric_mini.ui.renderers import diff_summary_rows, summarize_tool_result


def main() -> None:
    import streamlit as st

    args = _parse_args()
    st.set_page_config(page_title="netfabric-mini", layout="wide")
    st.title("netfabric-mini Developer UI")
    st.caption("Read-only console for simulated state, monitoring snapshots, agent traces, and eval rubrics.")

    db_path = Path(args.db)
    st.sidebar.write(f"DB: `{db_path}`")
    conn = data_access.connect_readonly(db_path)
    try:
        tabs = st.tabs([
            "Overview",
            "Simulation State",
            "Snapshots and Diffs",
            "Agent Runs",
            "Tool Trace",
            "Evidence Explorer",
            "Eval / Rubric",
        ])

        with tabs[0]:
            overview = data_access.get_overview(conn)
            st.metric("Topology", overview["topology_name"])
            st.metric("Current tick", overview["current_tick"])
            st.write({key: overview[key] for key in ("device_count", "link_count", "service_count", "latest_snapshot_id")})
            render_table(st, "Active Alerts", overview["active_alerts"])

        with tabs[1]:
            state = data_access.get_simulation_state(conn)
            render_table(st, "Devices", list(state["devices"].values()))
            render_table(st, "Links", list(state["links"].values()))
            render_table(st, "Services", list(state["services"].values()))
            render_table(st, "Probes", list(state["probes"].values()))
            render_json_expander(st, "Raw simulation state JSON", state)

        with tabs[2]:
            snapshots = data_access.get_snapshots_and_diff(conn)
            snapshot_ids = [snapshot["id"] for snapshot in snapshots["snapshots"]]
            from_id = st.selectbox("From snapshot", snapshot_ids, index=max(0, len(snapshot_ids) - 2)) if snapshot_ids else "latest-1"
            to_id = st.selectbox("To snapshot", snapshot_ids, index=max(0, len(snapshot_ids) - 1)) if snapshot_ids else "latest"
            snapshots = data_access.get_snapshots_and_diff(conn, from_id, to_id)
            render_table(st, "Snapshots", snapshots["snapshots"])
            render_table(st, "Diff Summary", diff_summary_rows(snapshots["diff"]))
            render_json_expander(st, "Snapshot diff JSON", snapshots["diff"])

        runs = data_access.list_agent_runs_readonly(conn)
        run_ids = [run["run_id"] for run in runs]
        selected_run = st.sidebar.selectbox("Agent run", run_ids) if run_ids else None

        with tabs[3]:
            render_table(st, "Agent Runs", runs)
            if selected_run:
                detail = data_access.get_agent_run_detail(conn, selected_run)
                render_json_expander(st, "Selected run detail", detail)

        with tabs[4]:
            if selected_run:
                calls = data_access.get_tool_trace(conn, selected_run)
                render_table(st, "Tool Calls", calls)
                for call in calls:
                    st.markdown(f"#### {call['tool_name']} / {call['trace_id']}")
                    st.json(summarize_tool_result(call["result"]))
                    render_json_expander(st, "Raw tool result", call["result"])
            else:
                st.caption("No agent run selected.")

        with tabs[5]:
            if selected_run:
                evidence = data_access.get_evidence_explorer(conn, selected_run)
                render_table(st, "Evidence", evidence["evidence"])
                render_json_expander(st, "Evidence explorer JSON", evidence)
            else:
                st.caption("No agent run selected.")

        with tabs[6]:
            if st.button("Run mock evals"):
                result = data_access.run_mock_evals_for_ui()
                render_json_expander(st, "Mock eval result", result)
    finally:
        conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
