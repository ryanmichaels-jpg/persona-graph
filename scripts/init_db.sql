-- Persona Graph — SQLite schema.
--
-- The DB itself is committed to the repo (data/intel.db) per Shawn Logan's
-- Nexus Intel pattern: the data layer is diffable, forkable, and ships with
-- the deploy. Scrapers are idempotent (INSERT OR IGNORE).

PRAGMA foreign_keys = ON;

-- --- Personas ---------------------------------------------------------------
-- The buyer persona being graphed. v1 has one row: "GTM Engineer".
CREATE TABLE IF NOT EXISTS personas (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- --- Content sources --------------------------------------------------------
-- The set of KOL handles / subreddits / Twitter handles we monitor.
CREATE TABLE IF NOT EXISTS content_sources (
    id           TEXT PRIMARY KEY,
    persona_id   TEXT NOT NULL REFERENCES personas(id),
    platform     TEXT NOT NULL CHECK (platform IN ('linkedin', 'reddit', 'twitter')),
    handle       TEXT NOT NULL,
    display_name TEXT,
    description  TEXT,
    follower_count INTEGER,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (platform, handle)
);

-- --- Content items ----------------------------------------------------------
-- Individual posts / tweets / threads.
CREATE TABLE IF NOT EXISTS content_items (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL REFERENCES content_sources(id),
    external_id     TEXT,
    url             TEXT,
    posted_at       TEXT NOT NULL,
    body_text       TEXT NOT NULL,
    reaction_count  INTEGER DEFAULT 0,
    comment_count   INTEGER DEFAULT 0,
    repost_count    INTEGER DEFAULT 0,
    raw_engagement  INTEGER DEFAULT 0,
    age_days        INTEGER,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_id);
CREATE INDEX IF NOT EXISTS idx_content_posted ON content_items(posted_at);

-- --- Topics + content<->topic m2m -----------------------------------------
-- Topics are Claude-extracted thematic tags ("AI tools", "RevOps frustration",
-- "CRM data quality", etc.). Color drives the d3-force node fill.
CREATE TABLE IF NOT EXISTS topics (
    id          TEXT PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    description TEXT,
    color       TEXT NOT NULL DEFAULT '#60a5fa',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS content_topics (
    content_id TEXT NOT NULL REFERENCES content_items(id),
    topic_id   TEXT NOT NULL REFERENCES topics(id),
    confidence REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (content_id, topic_id)
);

-- --- Signals + content<->signal m2m ----------------------------------------
-- Signals are pain language + buying signals + tool mentions.
CREATE TABLE IF NOT EXISTS signals (
    id          TEXT PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('pain', 'buying', 'tool_mention')),
    description TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS content_signals (
    content_id TEXT NOT NULL REFERENCES content_items(id),
    signal_id  TEXT NOT NULL REFERENCES signals(id),
    confidence REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (content_id, signal_id)
);

-- --- Engagers + content<->engager m2m ---------------------------------------
-- People who reacted / commented on content items.
CREATE TABLE IF NOT EXISTS engagers (
    id              TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    profile_url     TEXT,
    platform        TEXT CHECK (platform IN ('linkedin', 'reddit', 'twitter')),
    current_company TEXT,
    current_title   TEXT,
    company_size    INTEGER,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS content_engagers (
    content_id      TEXT NOT NULL REFERENCES content_items(id),
    engager_id      TEXT NOT NULL REFERENCES engagers(id),
    engagement_type TEXT NOT NULL CHECK (engagement_type IN ('reaction', 'comment', 'repost')),
    PRIMARY KEY (content_id, engager_id, engagement_type)
);

-- --- ICP scores (per engager, per persona) ---------------------------------
-- Borrowed scoring shape from gooseworks-ai/goose-skills/champion-tracker:
-- 4 dimensions, each 0-1, summed for total_score in [0, 4].
CREATE TABLE IF NOT EXISTS icp_scores (
    engager_id            TEXT NOT NULL REFERENCES engagers(id),
    persona_id            TEXT NOT NULL REFERENCES personas(id),
    b2b_score             REAL NOT NULL DEFAULT 0,
    seniority_score       REAL NOT NULL DEFAULT 0,
    company_size_score    REAL NOT NULL DEFAULT 0,
    gtm_relevance_score   REAL NOT NULL DEFAULT 0,
    total_score           REAL NOT NULL DEFAULT 0,
    tier                  TEXT NOT NULL CHECK (tier IN ('tier_1', 'tier_2', 'tier_3', 'not_icp')),
    scoring_notes         TEXT,
    scored_at             TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (engager_id, persona_id)
);
CREATE INDEX IF NOT EXISTS idx_icp_total ON icp_scores(total_score DESC);
