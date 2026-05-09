from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import typer

from netagent_lab import __version__
from netagent_lab.db import connect_db, init_db as init_sqlite_db
from netagent_lab.investigator import investigate_ticket
from netagent_lab.log_parser import parse_and_store_all
from netagent_lab.report import render_markdown_report, render_text_report
from netagent_lab.seed_loader import list_cases as list_available_cases
from netagent_lab.seed_loader import load_case
from netagent_lab.cli_sim import sim_app
from netagent_lab.cli_agent import agent_app

app = typer.Typer(
    name="netagent",
    help="NetAgent Lab network observability and incident investigation demos.",
    invoke_without_command=True,
    no_args_is_help=True,
)
app.add_typer(sim_app, name="sim")
app.add_typer(agent_app, name="agent")


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
    )
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("list-cases")
def list_cases_command() -> None:
    """Print available offline synthetic cases."""
    for case_name in list_available_cases():
        typer.echo(case_name)


@app.command("init-db")
def init_db_command(
    case: str = typer.Option(..., "--case", help="Offline case to load."),
    db: Path = typer.Option(..., "--db", help="SQLite database path."),
) -> None:
    """Create a SQLite DB and load one synthetic case."""
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = init_sqlite_db(db)
    summary = load_case(conn, case)
    conn.close()
    typer.echo(f"Loaded case {summary['case_name']} into {db}")


@app.command("parse-logs")
def parse_logs_command(
    db: Path = typer.Option(..., "--db", help="SQLite database path."),
) -> None:
    """Parse raw logs in an existing SQLite DB."""
    conn = connect_db(db)
    summary = parse_and_store_all(conn)
    conn.close()
    typer.echo(f"Parsed {summary['parsed_events']} events; skipped {summary['skipped_logs']} raw logs.")


@app.command("investigate")
def investigate_command(
    db: Path = typer.Option(..., "--db", help="SQLite database path."),
    ticket: str = typer.Option("T-001", "--ticket", help="Ticket ID to investigate."),
    output_format: str = typer.Option("markdown", "--format", help="Report format: markdown or text."),
) -> None:
    """Investigate a ticket from an existing SQLite DB."""
    conn = connect_db(db)
    result = investigate_ticket(conn, ticket)
    conn.close()
    typer.echo(_render(result, output_format))


@app.command("demo")
def demo_command(
    case: str = typer.Option("acl_block", "--case", help="Case name or 'all'."),
) -> None:
    """Run the full offline load, parse, investigate flow."""
    if case == "all":
        for case_name in list_available_cases():
            result = _run_demo_case(case_name)
            typer.echo(
                f"{case_name}: {result['root_cause_type']} "
                f"({result['confidence']}) - {result['summary']}"
            )
        return

    result = _run_demo_case(case)
    typer.echo(render_markdown_report(result))


@app.command("ui")
def ui_command(
    db: Path = typer.Option(..., "--db", help="SQLite simulation database path."),
) -> None:
    """Launch the optional read-only Streamlit developer UI."""
    if importlib.util.find_spec("streamlit") is None:
        typer.echo('Streamlit is not installed. Install it with: pip install -e ".[dev,ui]"', err=True)
        raise typer.Exit(code=1)
    app_path = Path(__file__).parent / "ui" / "streamlit_app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--", "--db", str(db)],
        check=False,
    )


def _run_demo_case(case_name: str) -> dict:
    conn = init_sqlite_db(":memory:")
    load_case(conn, case_name)
    parse_and_store_all(conn)
    result = investigate_ticket(conn, "T-001")
    conn.close()
    return result


def _render(result: dict, output_format: str) -> str:
    normalized = output_format.lower()
    if normalized == "markdown":
        return render_markdown_report(result)
    if normalized == "text":
        return render_text_report(result)
    raise typer.BadParameter("format must be 'markdown' or 'text'")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
