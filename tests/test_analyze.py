"""Analyze module tests — keyword-tagger correctness on known content."""

from __future__ import annotations

from pathlib import Path

import pytest

from persona_graph.analyze import analyze_all
from persona_graph.analyze.analyzer import _keyword_tag
from persona_graph.db import connect
from persona_graph.seed.generator import generate_seed


def test_keyword_finds_claude_mention():
    topics, signals = _keyword_tag("I asked Claude to scaffold a script yesterday.")
    topic_ids = [t for t, _ in topics]
    signal_ids = [s for s, _ in signals]
    assert "topic_ai_tools" in topic_ids
    assert "sig_tool_claude" in signal_ids


def test_keyword_finds_clay_cost_pain():
    topics, signals = _keyword_tag("Clay costs $500/mo for a feature I could write in Python.")
    signal_ids = [s for s, _ in signals]
    assert "sig_pain_clay_cost" in signal_ids
    assert "sig_tool_clay" in signal_ids


def test_keyword_finds_hiring_buying_signal():
    topics, signals = _keyword_tag("Hiring our first GTM Engineer at Series B SaaS company.")
    signal_ids = [s for s, _ in signals]
    assert "sig_buy_hire_gtm" in signal_ids


def test_keyword_finds_glue_code_pain():
    topics, signals = _keyword_tag(
        "I spent the week writing Python against the HubSpot API. RevOps is just glue code now."
    )
    signal_ids = [s for s, _ in signals]
    assert "sig_pain_glue_code" in signal_ids


def test_keyword_finds_salesforce_frustration():
    topics, signals = _keyword_tag("Salesforce is unusable — I keep exporting to Pandas.")
    topic_ids = [t for t, _ in topics]
    signal_ids = [s for s, _ in signals]
    assert "topic_crm_frustration" in topic_ids
    assert "sig_pain_export_sf" in signal_ids


def test_keyword_finds_clay_alternative_buying_signal():
    topics, signals = _keyword_tag("Looking for a Clay alternative under $200/mo. Recommendations?")
    signal_ids = [s for s, _ in signals]
    assert "sig_buy_clay_alt" in signal_ids


def test_keyword_random_text_returns_nothing():
    topics, signals = _keyword_tag("The weather is nice today.")
    assert topics == []
    assert signals == []


def test_full_analyze_on_seeded_db_increases_tags(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)

    with connect(db) as conn:
        topics_before = conn.execute("SELECT COUNT(*) FROM content_topics").fetchone()[0]
        signals_before = conn.execute("SELECT COUNT(*) FROM content_signals").fetchone()[0]

    counts = analyze_all(db_path=db, live=False)
    assert counts["mode"] == "keyword"
    assert counts["n_items_analyzed"] == 80
    # At least SOME new tags should land — keyword scan recall is higher than
    # the deterministic seed templates can cover for every post body
    assert counts["n_topic_tags_added"] + counts["n_signal_tags_added"] > 0

    with connect(db) as conn:
        topics_after = conn.execute("SELECT COUNT(*) FROM content_topics").fetchone()[0]
        signals_after = conn.execute("SELECT COUNT(*) FROM content_signals").fetchone()[0]
    assert topics_after >= topics_before
    assert signals_after >= signals_before


def test_analyze_hero_content_has_correct_tags(tmp_path: Path):
    """Hero post 003 (Brett's 'Hiring our first GTM Engineer' tweet) must
    have sig_buy_hire_gtm tagged after analyze."""
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    analyze_all(db_path=db, live=False)
    with connect(db) as conn:
        rows = conn.execute(
            "SELECT signal_id FROM content_signals WHERE content_id = 'post_hero_003'"
        ).fetchall()
    sigs = {r["signal_id"] for r in rows}
    assert "sig_buy_hire_gtm" in sigs
