"""Export SQLite intel DB to data/graph.json for the Next.js dashboard.

    python scripts/export_graph_data.py            # data/intel.db → data/graph.json
    python scripts/export_graph_data.py --db /tmp/x.db --out /tmp/g.json
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from persona_graph.export import export_graph_json  # noqa: E402

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def main(
    db: Path = typer.Option(Path("data/intel.db"), "--db"),
    out: Path = typer.Option(Path("data/graph.json"), "--out"),
):
    typer.echo(f"→ exporting {db} → {out}")
    written = export_graph_json(db_path=db, out_path=out)
    size_kb = written.stat().st_size // 1024
    typer.echo(f"✓ wrote {written} ({size_kb} KB)")


if __name__ == "__main__":
    app()
