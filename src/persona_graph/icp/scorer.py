"""4-dimension ICP scoring per engager, per persona.

Borrowed shape: gooseworks-ai/goose-skills `icp-persona-builder` +
`champion-tracker` — 4 axes each 0-1, summed for total in [0, 4].

Axes:
  b2b_score          — is the title B2B-relevant?
  seniority_score    — IC | Manager | Director | VP/Exec
  company_size_score — sweet spot is 100-2500 (Series A-D)
  gtm_relevance_score — how directly is this the GTM Engineer persona's
                       buying committee?

Tier thresholds:
  >= 3.0 → tier_1   (strong fit; this is the persona's buying committee)
  >= 2.0 → tier_2   (adjacent; might appear in deals but not lead)
  >= 1.0 → tier_3   (peripheral)
  <  1.0 → not_icp
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..db import connect


@dataclass
class ICPScore:
    engager_id: str
    persona_id: str
    b2b: float
    seniority: float
    company_size: float
    gtm_relevance: float
    total: float
    tier: str
    notes: str


# --- Scoring rules ----------------------------------------------------------


def score_b2b(title: str) -> float:
    """Is this title B2B-relevant?"""
    t = (title or "").lower()
    if any(k in t for k in ["software engineer", "developer", "data scientist", "designer", "ux"]):
        return 0.3
    if any(k in t for k in ["product manager", "engineering manager"]):
        return 0.5
    # Everything else (sales/marketing/exec/ops) is B2B
    return 1.0


def score_seniority(title: str) -> float:
    t = (title or "").lower()
    # C-level + VP
    if any(k in t for k in ["chief ", "cro", "cmo", "coo", "cfo", "vp ", "vp of", "founder", "ceo", "president"]):
        return 1.0
    # Director, Head of
    if any(k in t for k in ["director", "head of"]):
        return 0.75
    # Manager, Lead, Senior
    if any(k in t for k in ["manager", "lead", "senior "]):
        return 0.5
    # IC
    return 0.25


def score_company_size(size: int | None) -> float:
    if not size:
        return 0.5
    # Sweet spot: 100-2500 (Series A-D, typical first-GTM-Engineer hire window)
    if 100 <= size <= 2500:
        return 1.0
    if 50 <= size < 100 or 2500 < size <= 5000:
        return 0.75
    if size < 50 or size > 10000:
        return 0.25
    return 0.5


def score_gtm_relevance(title: str) -> float:
    """How directly does this title sit in the GTM Engineer persona's buying committee?"""
    t = (title or "").lower()
    if "gtm engineer" in t:
        return 1.0
    if any(k in t for k in ["revops", "revenue operations", "sales operations"]):
        return 0.9
    if any(k in t for k in ["sales development manager", "growth"]):
        return 0.6
    if any(k in t for k in ["vp of sales", "chief revenue officer", "cro"]):
        return 0.5
    if any(k in t for k in ["sales", "marketing", "demand gen"]):
        return 0.4
    if any(k in t for k in ["founder", "ceo", "coo", "president"]):
        return 0.4
    if any(k in t for k in ["product", "engineer", "developer", "design"]):
        return 0.1
    return 0.3


def _tier_for(total: float) -> str:
    if total >= 3.0:
        return "tier_1"
    if total >= 2.0:
        return "tier_2"
    if total >= 1.0:
        return "tier_3"
    return "not_icp"


def compute_score(engager_row: dict, persona_id: str = "gtm_engineer") -> ICPScore:
    title = engager_row.get("current_title", "") or ""
    size = engager_row.get("company_size") or None
    b2b = score_b2b(title)
    sen = score_seniority(title)
    csz = score_company_size(size)
    gtm = score_gtm_relevance(title)
    total = b2b + sen + csz + gtm
    return ICPScore(
        engager_id=engager_row["id"],
        persona_id=persona_id,
        b2b=round(b2b, 2),
        seniority=round(sen, 2),
        company_size=round(csz, 2),
        gtm_relevance=round(gtm, 2),
        total=round(total, 2),
        tier=_tier_for(total),
        notes=f"title='{title}', size={size}",
    )


def score_all_engagers(db_path: Path | None = None, persona_id: str = "gtm_engineer") -> dict:
    """Score every engager, write to icp_scores. Returns tier distribution."""
    tier_counts: dict[str, int] = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "not_icp": 0}
    n_scored = 0
    with connect(db_path) as conn:
        rows = conn.execute("SELECT id, current_title, company_size FROM engagers").fetchall()
        for row in rows:
            score = compute_score(dict(row), persona_id)
            conn.execute(
                """INSERT OR REPLACE INTO icp_scores
                   (engager_id, persona_id, b2b_score, seniority_score, company_size_score,
                    gtm_relevance_score, total_score, tier, scoring_notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (score.engager_id, score.persona_id, score.b2b, score.seniority,
                 score.company_size, score.gtm_relevance, score.total, score.tier, score.notes),
            )
            tier_counts[score.tier] += 1
            n_scored += 1
    return {"n_scored": n_scored, **tier_counts}
