# CLAUDE.md — Persona Graph

Context for any Claude Code session working in this repo. Read this first.

---

## What this is

**Persona Graph** — buyer-persona intel graph. Project 5 of 5 in the GTM Engineer portfolio. Lives in the parent `GTME portfolio/` folder; see `../CLAUDE.md` for the master portfolio brief.

**The pitch (rep voice):** "Reps build mental models of their buyer persona from anecdote. What if you could see the actual content the persona consumes, the language they use, the people they follow — as a graph?"

**The meta-clever move:** the persona we graph is the **GTM Engineer**. The hiring manager scanning this portfolio IS the persona on the graph. They see themselves in the data.

**The flow:**
```
Apify CLI scrapers (LinkedIn KOLs + subreddits + X handles)  →  SQLite-in-git
                                                                       ↓
                                                  Claude (Haiku 4.5, batched)
                                                  tags content with:
                                                    • topics (AI tools, RevOps frustration, …)
                                                    • pain signals ("I hate exporting from SF")
                                                    • buying signals (hiring posts, RFP mentions)
                                                  scores engagers on 4-dim ICP fit
                                                                       ↓
                                                  Next.js dashboard
                                                  • d3-force graph: sources → content → engagers
                                                  • color by topic, size by ICP score
                                                  • sidebar filter by signal type
```

---

## Stack

- **Data layer:** SQLite, committed to git as `data/intel.db` — Shawn Logan's Nexus Intel pattern. `git log data/intel.db` is the audit trail; `git checkout <sha> -- data/intel.db` time-travels the dataset.
- **Scrapers:** Apify CLI (`apify call <actor-id> --input <json>`). Specific actors per Shawn: `harvestapi` for LinkedIn, `apidojo/tweet-scraper` for X, `trudax/reddit-scraper-lite` for Reddit. **Optional** — synthetic seed is committed so the demo runs offline.
- **Analysis:** Anthropic Claude — **Haiku 4.5** for content tagging (batched), **Sonnet 4.6** for the persona-summary narrative in the dashboard. Used via the SDK (not subprocess — see "Differences from Shawn" below).
- **Dashboard:** Next.js 15 (App Router) + d3-force + better-sqlite3. Server-renders the graph data from SQLite — no API hop. Dark theme, matches the cleanroom + pipeline-resurrection report design system.
- **Deploy:** Railway (read-only DB on prod, writes happen locally then commit-push). **Optional** — demo can be local + screenshot.

---

## Repo conventions

- **`data/intel.db` IS committed** — the synthetic seed dataset. Real scrape outputs go to `data/raw_scrapes/` (gitignored).
- All credentials in `.env` (never committed). `.env.example` shows the shape.
- `DRY_RUN=1` in `.env` is the demo-safe default: heuristic tagger (no LLM calls) + skip live Apify scrapes.
- Slash command at `.claude/commands/persona-graph.md` is the user-facing API.
- One smoke test minimum: `tests/test_smoke.py`.
- macOS gotcha replicated: `scripts/setup.sh` runs `chflags -R nohidden .venv`.
- Idempotent scrapers — `INSERT OR IGNORE` into SQLite (safe to re-run on cron).

---

## Vendored / borrowed (credit in README)

| Pattern | Source | Where it lands |
|---|---|---|
| **SQLite-in-git as the data layer** | **Shawn Logan's Nexus Intel (Chapter 12 of gtm-coding-agent)** | `data/intel.db` + the whole schema philosophy |
| Apify CLI scraper pattern (`apify call <actor-id>`) | Shawn's Nexus Intel | `src/persona_graph/scrape/` (optional path) |
| Read-only SQLite from a Next.js server component | Shawn's Nexus Intel | `lib/db.ts` + `app/page.tsx` |
| 4-dimension ICP scoring (b2b + seniority + size + relevance) | gooseworks-ai/goose-skills → `icp-persona-builder` + `champion-tracker` | `src/persona_graph/icp/scorer.py` |
| Pain-language signal taxonomy | gooseworks-ai/goose-skills → `pain-language-engagers` | `src/persona_graph/analyze/signals.py` |
| Voice-of-customer synthesis | gooseworks-ai/goose-skills → `voice-of-customer-synthesizer` | dashboard persona-summary narrative |

## Differences from Shawn's Nexus Intel (be honest in the README)

- **Claude via SDK, not subprocess.** Shawn uses `claude --print` for batches. We use the Anthropic SDK because the other 4 portfolio projects use the SDK, and consistency beats marginal cost at <100-item scale.
- **No Railway deploy in v1.** Local + screenshot for the Loom. Railway deploy documented in `docs/demo.md` as optional.
- **One persona, not many.** Schema supports multiple personas but the seeded DB only has GTM Engineer. Adding more is the obvious v2 extension.

---

## Don't

- Don't build customer-facing app polish on the Next.js side. Per master portfolio CLAUDE.md: "internal dashboard, not a customer app." Minimal styling.
- Don't actually run Apify scrapes in `--live` mode without checking the Apify dashboard balance first ($3/scrape across 10 sources).
- Don't install gooseworks-ai/goose-skills as a dependency. Architectural reference only.
- Don't commit real LinkedIn/X scrape data. PII concerns; synthetic only is the demo path.
- Don't add auth / API routes / database mutations. The Next.js side is read-only — it queries the committed SQLite and renders.

---

## Quick orient for a new session

1. Read this file.
2. Read `../research-notes.md` § 1 (Shawn Logan's Nexus Intel) — the source of the SQLite-in-git pattern.
3. Read `README.md` for the public framing.
4. Read `.claude/commands/persona-graph.md` for the user-facing flow.
5. `src/persona_graph/` is the Python pipeline. `app/` + `components/` is the Next.js dashboard. `data/intel.db` is the data layer.

---

## Build order (where we are)

Phase 1 — scaffold ✅
Phase 2 — seed (synthetic content for GTM Engineer persona)
Phase 3 — analyze (Claude tags topics + pain language + signals)
Phase 4 — ICP scoring + SQLite query layer
Phase 5 — Next.js dashboard + d3-force graph
Phase 6 — slash command + README polish + verification
