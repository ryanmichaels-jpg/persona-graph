"""Export the SQLite intel DB as data/graph.json for the Next.js dashboard.

Schema of graph.json (the shape app/page.tsx + components/PersonaGraph.tsx
consume — change this and you change both sides):

  {
    "persona":  { id, name, description },
    "topics":   [ { id, name, color, content_count } ],
    "signals":  [ { id, name, signal_type, content_count } ],
    "nodes":    [ ... ],   # 3 node types: source / content / engager
    "edges":    [ ... ],   # authored (source→content) + engaged (engager→content)
    "stats":    { n_sources, n_content_items, n_engagers, tier_distribution, … }
  }
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .db import connect


# Tier → engager node color
_TIER_COLOR = {
    "tier_1":  "#4ade80",   # green
    "tier_2":  "#fbbf24",   # amber
    "tier_3":  "#f97316",   # orange
    "not_icp": "#64748b",   # slate-grey
}


def _primary_topic_for(content_id: str, conn) -> dict | None:
    """Highest-confidence topic for a content item."""
    row = conn.execute(
        """SELECT t.id, t.name, t.color, ct.confidence
             FROM content_topics ct JOIN topics t ON t.id = ct.topic_id
            WHERE ct.content_id = ?
            ORDER BY ct.confidence DESC LIMIT 1""",
        (content_id,),
    ).fetchone()
    return dict(row) if row else None


def build_graph(db_path: Path | None = None) -> dict:
    with connect(db_path) as conn:
        persona = dict(conn.execute("SELECT id, name, description FROM personas LIMIT 1").fetchone())

        # --- Topics + signals (with content counts) -----------------------
        topic_rows = conn.execute(
            """SELECT t.id, t.name, t.color,
                      (SELECT COUNT(*) FROM content_topics ct WHERE ct.topic_id = t.id) AS content_count
                 FROM topics t
                ORDER BY content_count DESC"""
        ).fetchall()
        topics = [dict(r) for r in topic_rows]

        signal_rows = conn.execute(
            """SELECT s.id, s.name, s.signal_type,
                      (SELECT COUNT(*) FROM content_signals cs WHERE cs.signal_id = s.id) AS content_count
                 FROM signals s
                ORDER BY s.signal_type, content_count DESC"""
        ).fetchall()
        signals = [dict(r) for r in signal_rows]

        # --- Source nodes ------------------------------------------------
        source_rows = conn.execute(
            """SELECT id, platform, handle, display_name, follower_count,
                      (SELECT COUNT(*) FROM content_items ci WHERE ci.source_id = cs.id) AS content_count
                 FROM content_sources cs"""
        ).fetchall()
        nodes: list[dict] = []
        for s in source_rows:
            nodes.append({
                "id": s["id"],
                "type": "source",
                "label": s["display_name"] or s["handle"],
                "platform": s["platform"],
                "follower_count": s["follower_count"],
                "content_count": s["content_count"],
                "color": "#ec4899",   # pink for sources
                "size": 16 + min(8, (s["content_count"] or 0)),
            })

        # --- Content nodes ----------------------------------------------
        content_rows = conn.execute(
            """SELECT id, source_id, body_text, reaction_count, comment_count, raw_engagement, age_days
                 FROM content_items"""
        ).fetchall()
        content_topics = {}   # content_id -> [topic_ids]
        for r in conn.execute("SELECT content_id, topic_id FROM content_topics").fetchall():
            content_topics.setdefault(r["content_id"], []).append(r["topic_id"])
        content_signals: dict[str, list[str]] = {}
        for r in conn.execute("SELECT content_id, signal_id FROM content_signals").fetchall():
            content_signals.setdefault(r["content_id"], []).append(r["signal_id"])

        for c in content_rows:
            primary = _primary_topic_for(c["id"], conn)
            label = c["body_text"][:80].replace("\n", " ") + ("…" if len(c["body_text"]) > 80 else "")
            engagement = c["raw_engagement"] or 0
            nodes.append({
                "id": c["id"],
                "type": "content",
                "label": label,
                "full_text": c["body_text"],
                "source_id": c["source_id"],
                "engagement": engagement,
                "age_days": c["age_days"],
                "topic_ids": content_topics.get(c["id"], []),
                "signal_ids": content_signals.get(c["id"], []),
                "primary_topic_id": primary["id"] if primary else None,
                "color": (primary["color"] if primary else "#94a3b8"),
                "size": 5 + min(15, engagement // 50),
                "is_hero": c["id"].startswith("post_hero_"),
            })

        # --- Engager nodes ----------------------------------------------
        engager_rows = conn.execute(
            """SELECT e.id, e.display_name, e.profile_url, e.platform, e.current_company,
                      e.current_title, e.company_size,
                      icp.b2b_score, icp.seniority_score, icp.company_size_score,
                      icp.gtm_relevance_score, icp.total_score, icp.tier
                 FROM engagers e
                 LEFT JOIN icp_scores icp ON icp.engager_id = e.id"""
        ).fetchall()
        for e in engager_rows:
            tier = e["tier"] or "not_icp"
            total = e["total_score"] or 0
            nodes.append({
                "id": e["id"],
                "type": "engager",
                "label": e["display_name"],
                "company": e["current_company"],
                "title": e["current_title"],
                "company_size": e["company_size"],
                "platform": e["platform"],
                "icp_score": round(total, 2),
                "tier": tier,
                "color": _TIER_COLOR.get(tier, _TIER_COLOR["not_icp"]),
                "size": 4 + total * 2.5,   # tier_1 ≈ 12, not_icp ≈ 4
                "score_breakdown": {
                    "b2b": e["b2b_score"], "seniority": e["seniority_score"],
                    "company_size": e["company_size_score"], "gtm_relevance": e["gtm_relevance_score"],
                },
            })

        # --- Edges -------------------------------------------------------
        edges: list[dict] = []
        # authored: source → content
        for c in content_rows:
            edges.append({"source": c["source_id"], "target": c["id"], "type": "authored", "weight": 1})
        # engaged: engager → content
        for r in conn.execute("SELECT content_id, engager_id, engagement_type FROM content_engagers").fetchall():
            weight = 2 if r["engagement_type"] == "comment" else 1
            edges.append({"source": r["engager_id"], "target": r["content_id"],
                          "type": "engaged", "weight": weight, "engagement_type": r["engagement_type"]})

        # --- Stats -------------------------------------------------------
        tier_counter: Counter = Counter()
        for e in engager_rows:
            tier_counter[e["tier"] or "not_icp"] += 1
        stats = {
            "n_sources": len(source_rows),
            "n_content_items": len(content_rows),
            "n_engagers": len(engager_rows),
            "n_topics": len(topic_rows),
            "n_signals": len(signal_rows),
            "n_engagements": sum(1 for e in edges if e["type"] == "engaged"),
            "tier_distribution": dict(tier_counter),
            "tier_colors": _TIER_COLOR,
        }

        return {
            "persona": persona,
            "topics": topics,
            "signals": signals,
            "nodes": nodes,
            "edges": edges,
            "stats": stats,
        }


def export_graph_json(db_path: Path | None = None, out_path: Path | None = None) -> Path:
    out_path = out_path or Path("data/graph.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_graph(db_path)
    out_path.write_text(json.dumps(data, indent=2, default=str))
    return out_path
