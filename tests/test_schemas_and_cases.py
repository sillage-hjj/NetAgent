from pathlib import Path

import yaml

from netagent_lab.schemas import (
    AclRulesFile,
    MetricsFile,
    TicketsFile,
    TopologyFile,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = PROJECT_ROOT / "data" / "cases"


def test_all_case_files_validate_against_schemas() -> None:
    for case_dir in sorted(CASES_DIR.iterdir()):
        TopologyFile.model_validate(yaml.safe_load((case_dir / "topology.yaml").read_text()))
        AclRulesFile.model_validate(yaml.safe_load((case_dir / "acl_rules.yaml").read_text()))
        MetricsFile.model_validate(yaml.safe_load((case_dir / "metrics.yaml").read_text()))
        TicketsFile.model_validate(yaml.safe_load((case_dir / "tickets.yaml").read_text()))


def test_cases_declare_expected_scenarios() -> None:
    expected = {"link_down", "acl_block", "performance_degradation"}

    assert {path.name for path in CASES_DIR.iterdir() if path.is_dir()} == expected

