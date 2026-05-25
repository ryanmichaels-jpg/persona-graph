"""Content tagger — Claude Haiku 4.5 in --live, keyword scan in dry-run.

Reads content_items from SQLite, derives:
  - topics       (which of the 8 thematic buckets does this fit)
  - pain signals ("I hate ...", "spent X hours ...")
  - buying signals ("hiring ...", "looking for ...")
  - tool mentions (Claude, Apollo, Clay by name)

Writes via INSERT OR IGNORE so existing seed tags stay; this stage ADDS
tags it discovers, never deletes. Same bounded-agent shape vendored from
reply-guy: one Claude call per item, structured JSON output, no tool loop.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..db import connect


# --- Keyword → topic/signal mapping (dry-run mode) --------------------------

# Each rule: (regex, ids_to_tag_to, kind, confidence)
_KEYWORD_RULES: list[tuple[re.Pattern, list[str], str, float]] = [
    # --- AI tooling ---
    (re.compile(r"\bclaude\b|\banthropic\b|\bllm\b|\bagent\b|\bmcp\b", re.IGNORECASE),
     ["topic_ai_tools", "sig_tool_claude"], "topic+signal", 0.85),
    (re.compile(r"\bchatgpt\b|\bgpt-?\d?\b|\bcursor\b", re.IGNORECASE),
     ["topic_ai_tools"], "topic", 0.7),

    # --- CRM frustration ---
    (re.compile(r"\bsalesforce\b", re.IGNORECASE),
     ["topic_crm_frustration", "sig_pain_export_sf"], "topic+signal", 0.8),
    (re.compile(r"\bhubspot\b", re.IGNORECASE),
     ["topic_crm_frustration"], "topic", 0.7),
    (re.compile(r"hubspot.*workflow|workflow.*broke", re.IGNORECASE),
     ["sig_pain_hs_wf"], "signal", 0.8),
    (re.compile(r"i (hate|can't stand|loathe).{0,40}(export|workflow|salesforce|hubspot)", re.IGNORECASE),
     ["sig_pain_export_sf"], "signal", 0.85),

    # --- RevOps automation ---
    (re.compile(r"\bclay\b", re.IGNORECASE),
     ["topic_revops_automation", "sig_tool_clay"], "topic+signal", 0.8),
    (re.compile(r"clay.{0,40}\$\d+|\$\d+/mo.{0,20}clay|clay.{0,20}costs?", re.IGNORECASE),
     ["sig_pain_clay_cost"], "signal", 0.9),
    (re.compile(r"\bclay alternative\b|alternative to clay", re.IGNORECASE),
     ["sig_buy_clay_alt"], "signal", 0.95),
    (re.compile(r"\bn8n\b|\bzapier\b", re.IGNORECASE),
     ["topic_revops_automation"], "topic", 0.7),
    (re.compile(r"\bapollo\b", re.IGNORECASE),
     ["sig_tool_apollo"], "signal", 0.85),
    (re.compile(r"\bautomat|\bscript|\bcron\b", re.IGNORECASE),
     ["topic_revops_automation"], "topic", 0.6),

    # --- Data quality ---
    (re.compile(r"\bdedup|\benrich|\bdata (quality|hygiene)\b|\bwaterfall\b", re.IGNORECASE),
     ["topic_data_quality"], "topic", 0.75),
    (re.compile(r"\bgarbage\b.{0,30}(crm|data|account)|\bblank\b.{0,30}(industry|country|field)", re.IGNORECASE),
     ["topic_data_quality"], "topic", 0.8),

    # --- Outbound sequencing ---
    (re.compile(r"\bsequenc|\bcold (email|outreach)\b|\boutreach\b", re.IGNORECASE),
     ["topic_outbound_sequencing"], "topic", 0.75),

    # --- Hiring GTM Engineer ---
    (re.compile(r"hiring.{0,30}(gtm engineer|first.{0,15}gtm|revops)", re.IGNORECASE),
     ["topic_hiring_gtm_eng", "sig_buy_hire_gtm"], "topic+signal", 0.95),
    (re.compile(r"\bgtm engineer\b|\bgtm-engineer\b", re.IGNORECASE),
     ["topic_hiring_gtm_eng"], "topic", 0.6),

    # --- Pipeline review ---
    (re.compile(r"\bstale (deal|list)|\bpipeline review\b|\bclosed-?lost\b|\bchampion\b", re.IGNORECASE),
     ["topic_pipeline_review"], "topic", 0.8),
    (re.compile(r"spent \d+ hours.{0,30}(stale|deal|list)|stale list (again|too long)", re.IGNORECASE),
     ["sig_pain_stale_list"], "signal", 0.9),

    # --- Career transitions ---
    (re.compile(r"\bsdr\b|\bae\b.{0,5}revops|career arc|\bex-rep\b", re.IGNORECASE),
     ["topic_career_transitions"], "topic", 0.7),
    (re.compile(r"glue code|just python|writing.{0,15}python.{0,15}(against|to hit)", re.IGNORECASE),
     ["sig_pain_glue_code"], "signal", 0.85),

    # --- Generic buying signals ---
    (re.compile(r"what.{0,15}everyone (using|on)|what's everyone", re.IGNORECASE),
     ["sig_buy_what_using"], "signal", 0.85),
    (re.compile(r"\brfp\b|active rfp|vendor evaluation", re.IGNORECASE),
     ["sig_buy_rfp"], "signal", 0.85),
]


@dataclass
class TaggingResult:
    content_id: str
    topics: list[tuple[str, float]]   # [(topic_id, confidence)]
    signals: list[tuple[str, float]]
    source: str                       # "keyword" | "claude-haiku-4-5"


# --- Live (Claude Haiku 4.5) ------------------------------------------------

_LIVE_PROMPT = """You are tagging a piece of social content for a GTM-engineer persona graph.

Available topic IDs (pick all that apply):
  topic_ai_tools, topic_crm_frustration, topic_revops_automation, topic_data_quality,
  topic_outbound_sequencing, topic_hiring_gtm_eng, topic_pipeline_review, topic_career_transitions

Available signal IDs (pick all that apply, leave [] if none):
  pain:         sig_pain_export_sf, sig_pain_clay_cost, sig_pain_hs_wf, sig_pain_glue_code, sig_pain_stale_list
  buying:       sig_buy_hire_gtm, sig_buy_clay_alt, sig_buy_what_using, sig_buy_rfp
  tool_mention: sig_tool_claude, sig_tool_apollo, sig_tool_clay

Content:
\"\"\"{body}\"\"\"

Return ONLY JSON, no markdown:
{{"topics": ["topic_x", ...], "signals": ["sig_x", ...]}}"""


def _live_tag(body_text: str, client) -> tuple[list[str], list[str]]:
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": _LIVE_PROMPT.format(body=body_text[:1000])}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        data = json.loads(text)
        return (list(data.get("topics", [])), list(data.get("signals", [])))
    except Exception:
        return ([], [])


# --- Dry-run (keyword scan) -------------------------------------------------


def _keyword_tag(body_text: str) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    topics: dict[str, float] = {}
    signals: dict[str, float] = {}
    for pattern, ids, kind, conf in _KEYWORD_RULES:
        if not pattern.search(body_text):
            continue
        for tid in ids:
            if tid.startswith("topic_"):
                topics[tid] = max(topics.get(tid, 0.0), conf)
            elif tid.startswith("sig_"):
                signals[tid] = max(signals.get(tid, 0.0), conf)
    return (sorted(topics.items()), sorted(signals.items()))


# --- Orchestrator ----------------------------------------------------------


def analyze_all(
    db_path: Path | None = None,
    live: bool = False,
) -> dict[str, int]:
    """Tag every content item. Returns counts."""
    client = None
    if live:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError("anthropic SDK not installed — pip install -e .") from e
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set; cannot run live")
        client = Anthropic()

    n_items = 0
    n_topics_added = 0
    n_signals_added = 0

    with connect(db_path) as conn:
        rows = conn.execute("SELECT id, body_text FROM content_items").fetchall()
        for row in rows:
            cid = row["id"]
            body = row["body_text"]
            if live:
                topic_ids, signal_ids = _live_tag(body, client)
                topic_pairs = [(t, 0.85) for t in topic_ids]
                signal_pairs = [(s, 0.85) for s in signal_ids]
            else:
                topic_pairs, signal_pairs = _keyword_tag(body)

            for tid, conf in topic_pairs:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO content_topics (content_id, topic_id, confidence) VALUES (?, ?, ?)",
                    (cid, tid, conf),
                )
                if cur.rowcount > 0:
                    n_topics_added += 1
            for sid, conf in signal_pairs:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO content_signals (content_id, signal_id, confidence) VALUES (?, ?, ?)",
                    (cid, sid, conf),
                )
                if cur.rowcount > 0:
                    n_signals_added += 1
            n_items += 1

    return {
        "n_items_analyzed": n_items,
        "n_topic_tags_added": n_topics_added,
        "n_signal_tags_added": n_signals_added,
        "mode": "live" if live else "keyword",
    }
