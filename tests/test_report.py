from netagent_lab.db import init_db
from netagent_lab.investigator import investigate_ticket
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.report import render_markdown_report
from netagent_lab.seed_loader import load_case


def test_markdown_report_contains_root_cause_evidence_and_tool_trace() -> None:
    conn = init_db(":memory:")
    load_case(conn, "acl_block")
    parse_and_store_all(conn)
    result = investigate_ticket(conn, "T-001")

    report = render_markdown_report(result)

    assert "acl_block" in report
    assert "ACL-DENY-ZRH-APPB-HTTPS" in report
    assert "infer_path" in report
    assert "executed remediation" not in report.lower()
    assert "Remediation was not executed" in report

