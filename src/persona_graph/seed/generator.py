"""Synthetic content generator for the GTM Engineer persona.

Reads seed_config.yaml, writes directly to SQLite (the canonical data layer).
Idempotent: re-running on a fresh DB produces byte-identical output for the
same seed (Shawn's Nexus Intel pattern — diffable data layer).

Content shape:
  - 10 sources (5 LinkedIn KOLs + 3 subreddits + 5 Twitter handles)
  - 8 topics + 12 signals (4 pain / 4 buying / 4 tool_mention)
  - ~80 content items (5 hero + 75 random)
  - ~40 engagers (mixed titles to produce a 4-tier ICP distribution)
"""

from __future__ import annotations

import hashlib
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from faker import Faker

from ..db import reset_db, connect


SEED_CONFIG = Path(__file__).parent / "seed_config.yaml"


def _now() -> datetime:
    return datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)


def _content_id_for(idx: int, prefix: str = "post") -> str:
    return f"{prefix}_{idx:05d}"


def _engager_id_for(idx: int) -> str:
    return f"eng_{idx:05d}"


def _stable_hash(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16)


# --- Sample non-hero post bodies ---------------------------------------------
# Snippet templates per topic, mixed deterministically by hash. Each one
# encodes 1-2 pain/buy/tool signals so the analyze stage has something to find.

_POST_BODIES = {
    "topic_ai_tools": [
        "Claude wrote 80% of my last RevOps script. I reviewed the rest. Wild times.",
        "Cursor + Claude is now my CRM stack. I haven't opened HubSpot's UI in weeks.",
        "Anthropic's MCP is the right abstraction for GTM tooling. Change my mind.",
        "Asked Claude to draft an Apollo waterfall yesterday. Saved me a Clay subscription.",
    ],
    "topic_crm_frustration": [
        "Salesforce reports take longer to build than the analysis itself.",
        "HubSpot workflows broke silently for 3 weeks and nobody noticed.",
        "Our CRM is 40% garbage. I keep exporting to Pandas and fixing it there.",
        "If your VP of Sales is still pulling reports manually in 2026, we have problems.",
    ],
    "topic_revops_automation": [
        "Replaced $500/mo Clay tier with a 200-line Python script. Honest GTM ROI.",
        "n8n is a gateway drug. Three weeks in I was writing my own Apollo client.",
        "Don't pay for SaaS that wraps a free API. It's a 90-minute Python script.",
        "Looking for a Clay alternative that's not also $349/mo. Recommendations?",
    ],
    "topic_data_quality": [
        "Spent the weekend deduping 5,000 accounts. Rapidfuzz + Claude tie-breaker = 3 minutes.",
        "Our 'Customer' stage has accounts with zero contacts. That's not a customer.",
        "Apollo waterfall hits 70% coverage. Clay charges 5x for the last 10%.",
        "Industry blank on 30% of accounts is the most common CRM smell.",
    ],
    "topic_outbound_sequencing": [
        "Generic sequences are spam. Personalized at scale is the only viable cold motion.",
        "Cold email open rates are vanity. Reply rate is the only number that matters.",
        "Stopped using sequencing tools. Just Python + Claude + the rep's calendar now.",
        "If your sequence has 9+ touches, you don't have a sequence, you have a stalker.",
    ],
    "topic_hiring_gtm_eng": [
        "Hiring our first GTM Engineer. Must have closed a deal AND shipped a Python script.",
        "GTM Engineer JD update: dropped the 'full-stack' requirement. We just need someone who shipped.",
        "Looking for a GTM Engineer at Series B SaaS. Stop applying to FAANG, this is more fun.",
        "If you can build a Clay table AND a HubSpot workflow, DMs open. Archetype A.",
    ],
    "topic_pipeline_review": [
        "Monday pipeline review is 80% theatre and 20% actually working the stale list.",
        "If 60+ days have passed and there's no fresh signal, the deal is dead. Disqualify.",
        "Pulled all closed-lost deals from 2024 with 'bad timing'. Half of them got funded since.",
        "Champion tracking is the highest-ROI thing nobody does. Apollo + a cron job.",
    ],
    "topic_career_transitions": [
        "SDR → AE → RevOps → GTM Engineer. The progression is real and underpriced.",
        "Ex-rep with Python > full-stack engineer learning sales. Empirically every time.",
        "My title is RevOps Manager but I write more Python than my engineering team.",
        "GTM Engineer is the only role in 2026 where rep experience is a feature, not a bug.",
    ],
}


# --- Generation -------------------------------------------------------------


def _insert_persona(conn: sqlite3.Connection, config: dict) -> None:
    p = config["persona"]
    conn.execute(
        "INSERT OR REPLACE INTO personas (id, name, description) VALUES (?, ?, ?)",
        (p["id"], p["name"], p["description"]),
    )


def _insert_sources(conn: sqlite3.Connection, config: dict) -> None:
    persona_id = config["persona"]["id"]
    for s in config["content_sources"]:
        conn.execute(
            """INSERT OR REPLACE INTO content_sources
               (id, persona_id, platform, handle, display_name, description, follower_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (s["id"], persona_id, s["platform"], s["handle"],
             s.get("display_name"), s.get("description"), s.get("follower_count")),
        )


def _insert_topics_and_signals(conn: sqlite3.Connection, config: dict) -> None:
    for t in config["topics"]:
        conn.execute(
            "INSERT OR REPLACE INTO topics (id, name, description, color) VALUES (?, ?, ?, ?)",
            (t["id"], t["name"], t.get("description"), t.get("color", "#60a5fa")),
        )
    for s in config["signals"]:
        conn.execute(
            "INSERT OR REPLACE INTO signals (id, name, signal_type, description) VALUES (?, ?, ?, ?)",
            (s["id"], s["name"], s["signal_type"], s.get("description")),
        )


def _insert_hero_content(conn: sqlite3.Connection, config: dict) -> list[str]:
    """Returns list of hero content_ids in insertion order."""
    now = _now()
    rng = random.Random(config["random_seed"])
    inserted_ids: list[str] = []
    for hero in config["hero_content"]:
        days_old = rng.randint(3, 21)   # heroes are recent
        posted = now - timedelta(days=days_old)
        conn.execute(
            """INSERT OR REPLACE INTO content_items
               (id, source_id, url, posted_at, body_text, reaction_count, comment_count,
                raw_engagement, age_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (hero["id"], hero["source_id"], f"https://example/{hero['id']}",
             posted.isoformat(), hero["body_text"].strip(),
             hero["reaction_count"], hero["comment_count"],
             hero["reaction_count"] + hero["comment_count"], days_old),
        )
        for tid in hero["topics"]:
            conn.execute(
                "INSERT OR IGNORE INTO content_topics (content_id, topic_id, confidence) VALUES (?, ?, 1.0)",
                (hero["id"], tid),
            )
        for sid in hero["signals"]:
            conn.execute(
                "INSERT OR IGNORE INTO content_signals (content_id, signal_id, confidence) VALUES (?, ?, 1.0)",
                (hero["id"], sid),
            )
        inserted_ids.append(hero["id"])
    return inserted_ids


def _generate_random_content(
    conn: sqlite3.Connection, config: dict, start_idx: int
) -> list[str]:
    """Generate the non-hero content. Each post: one source, 1-3 topics, 0-3 signals.
    Pre-tagged with topics/signals deterministically — the analyze stage will
    re-derive these from text in --live mode."""
    rng = random.Random(config["random_seed"] + 7)
    now = _now()
    sources = config["content_sources"]
    topics = config["topics"]
    signals_all = config["signals"]
    cgen = config["content_generation"]

    n_target = cgen["total_items"] - len(config["hero_content"])
    body_topic_keys = list(_POST_BODIES.keys())
    inserted_ids: list[str] = []

    idx = start_idx
    for _ in range(n_target):
        src = rng.choice(sources)
        topic_key = rng.choice(body_topic_keys)
        body = rng.choice(_POST_BODIES[topic_key])
        days_old = rng.randint(*cgen["days_old_range"])
        posted = now - timedelta(days=days_old)
        reactions = rng.randint(*cgen["reactions_range"])
        comments = rng.randint(*cgen["comments_range"])
        cid = _content_id_for(idx)
        conn.execute(
            """INSERT OR IGNORE INTO content_items
               (id, source_id, url, posted_at, body_text, reaction_count, comment_count,
                raw_engagement, age_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, src["id"], f"https://example/{cid}", posted.isoformat(),
             body, reactions, comments, reactions + comments, days_old),
        )
        # Always tag at least the primary topic for the body
        conn.execute(
            "INSERT OR IGNORE INTO content_topics (content_id, topic_id, confidence) VALUES (?, ?, 0.9)",
            (cid, topic_key),
        )
        # Optional extra topics
        n_extra_topics = rng.randint(0, cgen["topics_per_item_range"][1] - 1)
        for extra in rng.sample([t["id"] for t in topics if t["id"] != topic_key],
                                 k=min(n_extra_topics, len(topics) - 1)):
            conn.execute(
                "INSERT OR IGNORE INTO content_topics (content_id, topic_id, confidence) VALUES (?, ?, 0.7)",
                (cid, extra),
            )
        # 0-3 signals — bias toward pain signals since those drive ICP relevance
        n_signals = rng.randint(*cgen["signals_per_item_range"])
        if n_signals:
            picked = rng.sample(signals_all, k=min(n_signals, len(signals_all)))
            for sig in picked:
                conn.execute(
                    "INSERT OR IGNORE INTO content_signals (content_id, signal_id, confidence) VALUES (?, ?, 0.8)",
                    (cid, sig["id"]),
                )
        inserted_ids.append(cid)
        idx += 1
    return inserted_ids


def _generate_engagers(conn: sqlite3.Connection, config: dict, all_content_ids: list[str]) -> list[str]:
    """Generate engagers with the configured title distribution + scatter their
    engagements across content items."""
    Faker.seed(config["random_seed"] + 13)
    fake = Faker("en_US")
    rng = random.Random(config["random_seed"] + 13)
    egen = config["engager_generation"]
    title_dist: dict[str, int] = egen["title_distribution"]
    sizes = egen["company_size_buckets"]

    # Flatten title distribution into an ordered list of titles
    titles: list[str] = []
    for t, n in title_dist.items():
        titles.extend([t] * n)
    rng.shuffle(titles)
    titles = titles[: egen["total_engagers"]]

    inserted_ids: list[str] = []
    for i, title in enumerate(titles, start=1):
        eid = _engager_id_for(i)
        platform = rng.choices(["linkedin", "reddit", "twitter"], weights=[0.6, 0.25, 0.15])[0]
        company = fake.company()
        company_size = rng.choice(sizes)
        conn.execute(
            """INSERT OR REPLACE INTO engagers
               (id, display_name, profile_url, platform, current_company, current_title, company_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (eid, fake.name(), f"https://example/profile/{eid}",
             platform, company, title, company_size),
        )
        # Scatter 1-6 engagements across content
        n_engagements = rng.randint(*egen["engagements_per_engager_range"])
        targets = rng.sample(all_content_ids, k=min(n_engagements, len(all_content_ids)))
        for cid in targets:
            etype = rng.choices(["reaction", "comment", "repost"], weights=[0.7, 0.25, 0.05])[0]
            conn.execute(
                """INSERT OR IGNORE INTO content_engagers
                   (content_id, engager_id, engagement_type) VALUES (?, ?, ?)""",
                (cid, eid, etype),
            )
        inserted_ids.append(eid)
    return inserted_ids


def generate_seed(db_path: Path | None = None, config_path: Path | None = None) -> dict[str, int]:
    """Populate the SQLite DB with a full synthetic dataset. Returns counts."""
    config = yaml.safe_load((config_path or SEED_CONFIG).read_text())
    reset_db(db_path)
    with connect(db_path) as conn:
        _insert_persona(conn, config)
        _insert_sources(conn, config)
        _insert_topics_and_signals(conn, config)
        hero_ids = _insert_hero_content(conn, config)
        random_ids = _generate_random_content(conn, config, start_idx=len(hero_ids) + 1)
        all_content_ids = hero_ids + random_ids
        engager_ids = _generate_engagers(conn, config, all_content_ids)

    # Re-read counts
    with connect(db_path) as conn:
        return {
            "personas": conn.execute("SELECT COUNT(*) FROM personas").fetchone()[0],
            "sources": conn.execute("SELECT COUNT(*) FROM content_sources").fetchone()[0],
            "content_items": conn.execute("SELECT COUNT(*) FROM content_items").fetchone()[0],
            "topics": conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0],
            "signals": conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
            "engagers": conn.execute("SELECT COUNT(*) FROM engagers").fetchone()[0],
            "content_topics": conn.execute("SELECT COUNT(*) FROM content_topics").fetchone()[0],
            "content_signals": conn.execute("SELECT COUNT(*) FROM content_signals").fetchone()[0],
            "content_engagers": conn.execute("SELECT COUNT(*) FROM content_engagers").fetchone()[0],
        }
