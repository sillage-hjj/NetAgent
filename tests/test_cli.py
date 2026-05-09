import pytest
from typer.testing import CliRunner

from netagent_lab.cli import app


@pytest.mark.parametrize(
    ("case_name", "root_cause_type"),
    [
        ("link_down", "link_down"),
        ("acl_block", "acl_block"),
        ("performance_degradation", "performance_degradation"),
    ],
)
def test_cli_demo_case_outputs_expected_root_cause(case_name: str, root_cause_type: str) -> None:
    result = CliRunner().invoke(app, ["demo", "--case", case_name])

    assert result.exit_code == 0
    assert root_cause_type in result.output


def test_cli_demo_all_outputs_short_summaries() -> None:
    result = CliRunner().invoke(app, ["demo", "--case", "all"])

    assert result.exit_code == 0
    assert "link_down" in result.output
    assert "acl_block" in result.output
    assert "performance_degradation" in result.output


def test_cli_list_cases() -> None:
    result = CliRunner().invoke(app, ["list-cases"])

    assert result.exit_code == 0
    assert "acl_block" in result.output
