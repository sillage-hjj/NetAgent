from __future__ import annotations

from typing import Any

from netagent_lab.ui.renderers import to_pretty_json


def render_json_expander(st, label: str, payload: Any) -> None:
    with st.expander(label):
        st.code(to_pretty_json(payload), language="json")


def render_table(st, title: str, rows: Any) -> None:
    st.subheader(title)
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.caption("No data available.")

