"""Seed determinism + hero-presence + storyline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from persona_graph.db import connect
from persona_graph.seed.generator import generate_seed


def test_seed_counts_in_expected_range(tmp_path: Path):
    db = tmp_path / "intel.db"
    counts = generate_seed(db_path=db)
    assert counts["personas"] == 1
    assert counts["sources"] == 10
    assert counts["topics"] == 8
    assert counts["signals"] == 12
    assert counts["content_items"] == 80
    assert counts["engagers"] == 40
    assert counts["content_engagers"] > 50   # 40 engagers × 1-6 each


def test_hero_content_present(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        rows = conn.execute(
            "SELECT id, body_text FROM content_items WHERE id LIKE 'post_hero_%' ORDER BY id"
        ).fetchall()
    assert len(rows) == 5
    bodies = " ".join(r["body_text"] for r in rows)
    # The Loom storyline anchor phrases must always be present
    assert "stale-deal scanner" in bodies
    assert "RevOps in 2026 is just LLM glue code" in bodies
    assert "Hiring our first GTM Engineer" in bodies
    assert "Clay is great" in bodies
    assert "Salesforce is unusable in 2026" in bodies


def test_persona_inserted_with_target_id(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        row = conn.execute("SELECT id, name FROM personas").fetchone()
    assert row["id"] == "gtm_engineer"
    assert row["name"] == "GTM Engineer"


def test_topics_have_colors(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        rows = conn.execute("SELECT name, color FROM topics").fetchall()
    assert len(rows) == 8
    for r in rows:
        assert r["color"].startswith("#")
        assert len(r["color"]) == 7


def test_signal_type_distribution(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        rows = conn.execute(
            "SELECT signal_type, COUNT(*) AS n FROM signals GROUP BY signal_type"
        ).fetchall()
    counts = {r["signal_type"]: r["n"] for r in rows}
    assert counts["pain"] == 5
    assert counts["buying"] == 4
    assert counts["tool_mention"] == 3


def test_hero_content_has_tagged_topics(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        rows = conn.execute(
            """SELECT c.id, COUNT(ct.topic_id) AS n_topics
                 FROM content_items c
                 LEFT JOIN content_topics ct ON ct.content_id = c.id
                WHERE c.id LIKE 'post_hero_%'
                GROUP BY c.id"""
        ).fetchall()
    for r in rows:
        assert r["n_topics"] >= 2, f"{r['id']} only has {r['n_topics']} topics"


def test_seed_reproducible(tmp_path: Path):
    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"
    generate_seed(db_path=db1)
    generate_seed(db_path=db2)
    with connect(db1) as c1, connect(db2) as c2:
        a = c1.execute("SELECT id, body_text FROM content_items ORDER BY id").fetchall()
        b = c2.execute("SELECT id, body_text FROM content_items ORDER BY id").fetchall()
    assert len(a) == len(b)
    for r_a, r_b in zip(a, b):
        assert r_a["id"] == r_b["id"]
        assert r_a["body_text"] == r_b["body_text"]


def test_engager_title_distribution_skews_to_persona(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    with connect(db) as conn:
        rows = conn.execute(
            "SELECT current_title, COUNT(*) AS n FROM engagers GROUP BY current_title"
        ).fetchall()
    title_counts = {r["current_title"]: r["n"] for r in rows}
    # GTM Engineer should be the largest single bucket (10 per config)
    assert title_counts.get("GTM Engineer", 0) >= 8
