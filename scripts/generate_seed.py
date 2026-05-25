"""CLI wrapper around the synthetic content seed generator.

Usage:
    python scripts/generate_seed.py                  # populate data/intel.db
    python scripts/generate_seed.py --db /tmp/x.db   # alternate DB path

Writes ~80 content items + 40 engagers + the GTM Engineer persona + tags
into a fresh SQLite DB (wipes existing rows).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from persona_graph.seed.generator import generate_seed  # noqa: E402

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    db: Path = typer.Option(Path("data/intel.db"), "--db", help="SQLite path"),
):
    typer.echo(f"→ generating synthetic GTM-Engineer-persona seed into {db}")
    counts = generate_seed(db_path=db)
    for k, v in counts.items():
        typer.echo(f"  {k:18} {v}")
    typer.echo("✓ seed complete.")


if __name__ == "__main__":
    app()
