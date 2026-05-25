"""ICP scoring + JSON export tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_graph.db import connect
from persona_graph.export import build_graph, export_graph_json
from persona_graph.icp import compute_score, score_all_engagers
from persona_graph.icp.scorer import (
    score_b2b,
    score_company_size,
    score_gtm_relevance,
    score_seniority,
)
from persona_graph.seed.generator import generate_seed


# --- Scoring rules ----------------------------------------------------------


def test_gtm_engineer_is_max_relevance():
    assert score_gtm_relevance("GTM Engineer") == 1.0
    assert score_gtm_relevance("Senior GTM Engineer") == 1.0


def test_software_engineer_is_low_b2b_and_low_relevance():
    assert score_b2b("Software Engineer") < 0.5
    assert score_gtm_relevance("Software Engineer") < 0.5


def test_vp_seniority_is_max():
    assert score_seniority("VP of Sales") == 1.0
    assert score_seniority("Chief Revenue Officer") == 1.0
    assert score_seniority("Founder & CEO") == 1.0


def test_director_seniority_below_vp():
    assert 0.5 < score_seniority("Director of Marketing") < 1.0


def test_manager_below_director():
    assert score_seniority("Senior RevOps Manager") < score_seniority("Director of RevOps")


def test_company_size_sweet_spot():
    assert score_company_size(250) == 1.0
    assert score_company_size(2500) == 1.0
    assert score_company_size(10) < 0.5
    assert score_company_size(50000) < 0.5


def test_gtm_engineer_at_ideal_size_is_tier_1():
    s = compute_score({"id": "x", "current_title": "GTM Engineer", "company_size": 250})
    assert s.tier == "tier_1"
    assert s.total >= 3.0


def test_software_engineer_at_ideal_size_is_tier_3():
    s = compute_score({"id": "x", "current_title": "Software Engineer", "company_size": 250})
    assert s.tier == "tier_3"


def test_founder_at_huge_company_drops_tier():
    s_small = compute_score({"id": "x", "current_title": "Founder & CEO", "company_size": 250})
    s_huge  = compute_score({"id": "x", "current_title": "Founder & CEO", "company_size": 50000})
    assert s_small.total > s_huge.total


# --- Integration ------------------------------------------------------------


def test_score_all_engagers_persists_tiers(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    counts = score_all_engagers(db_path=db)
    assert counts["n_scored"] == 40
    # Most engagers should be tier_1 or tier_2 (the seed skews GTM-Engineer-adjacent)
    assert counts["tier_1"] + counts["tier_2"] >= 25


def test_export_graph_json_writes_all_node_types(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    score_all_engagers(db_path=db)
    out = tmp_path / "graph.json"
    export_graph_json(db_path=db, out_path=out)
    assert out.exists()
    data = json.loads(out.read_text())
    types = {n["type"] for n in data["nodes"]}
    assert types == {"source", "content", "engager"}
    # Hero content must be present
    hero_nodes = [n for n in data["nodes"] if n.get("is_hero")]
    assert len(hero_nodes) == 5
    # Edges include both authored and engaged
    edge_types = {e["type"] for e in data["edges"]}
    assert edge_types == {"authored", "engaged"}
    # Stats sanity
    assert data["stats"]["n_sources"] == 10
    assert data["stats"]["n_content_items"] == 80
    assert data["stats"]["n_engagers"] == 40


def test_graph_engager_nodes_have_icp_scores(tmp_path: Path):
    db = tmp_path / "intel.db"
    generate_seed(db_path=db)
    score_all_engagers(db_path=db)
    graph = build_graph(db_path=db)
    engagers = [n for n in graph["nodes"] if n["type"] == "engager"]
    assert all("icp_score" in n for n in engagers)
    assert all("tier" in n for n in engagers)
    # GTM Engineer engagers should land in tier_1
    gtm_engineers = [n for n in engagers if n["title"] == "GTM Engineer"]
    assert len(gtm_engineers) >= 8
    assert all(n["tier"] == "tier_1" for n in gtm_engineers)
