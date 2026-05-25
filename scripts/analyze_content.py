"""CLI wrapper around the content tagger.

    python scripts/analyze_content.py            # dry-run (keyword scan)
    python scripts/analyze_content.py --live     # Claude Haiku 4.5
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from persona_graph.analyze import analyze_all  # noqa: E402

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    db: Path = typer.Option(Path("data/intel.db"), "--db"),
    live: bool = typer.Option(False, "--live", help="Use Claude Haiku 4.5 (else keyword scan)"),
):
    typer.echo(f"→ analyzing content in {db} ({'live' if live else 'dry-run'} mode)")
    counts = analyze_all(db_path=db, live=live)
    for k, v in counts.items():
        typer.echo(f"  {k:24} {v}")


if __name__ == "__main__":
    app()
