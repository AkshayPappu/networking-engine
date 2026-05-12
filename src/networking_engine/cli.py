import typer

from networking_engine import __version__
from networking_engine.pipeline import run_query

app = typer.Typer(
    name="scout",
    help="Evidence-grounded networking search over the public web (OpenAI + Tavily/Brave).",
    no_args_is_help=True,
)


@app.command("version")
def version_cmd() -> None:
    """Print the installed scout / networking-engine version."""
    typer.echo(__version__)


@app.command("query")
def query_cmd(
    text: str = typer.Argument(..., help="Natural-language networking query."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run planner only and print search strings (no search or ranking).",
    ),
) -> None:
    raise typer.Exit(run_query(text, dry_run=dry_run))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
