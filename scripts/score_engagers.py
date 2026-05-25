"""CLI wrapper around the ICP scorer.

    python scripts/score_engagers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from persona_graph.icp import score_all_engagers  # noqa: E402

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    db: Path = typer.Option(Path("data/intel.db"), "--db"),
    persona: str = typer.Option("gtm_engineer", "--persona"),
):
    typer.echo(f"→ scoring engagers vs persona '{persona}' in {db}")
    counts = score_all_engagers(db_path=db, persona_id=persona)
    typer.echo(f"  scored:    {counts['n_scored']}")
    typer.echo(f"  tier_1:    {counts['tier_1']}")
    typer.echo(f"  tier_2:    {counts['tier_2']}")
    typer.echo(f"  tier_3:    {counts['tier_3']}")
    typer.echo(f"  not_icp:   {counts['not_icp']}")


if __name__ == "__main__":
    app()
