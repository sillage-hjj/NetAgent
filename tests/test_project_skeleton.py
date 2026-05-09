from typer.testing import CliRunner

from netagent_lab import __version__
from netagent_lab.cli import app


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output

