# Persona Graph

> Reps build mental models of their buyer persona from anecdote. "Our buyer is a VP of Sales at a Series B SaaS company, probably tired of Salesforce, follows a few people on LinkedIn." Cool. Now show me which LinkedIn posts they actually engage with, which tools they complain about by name, which subreddits they lurk in, and which other people you'd be selling to alongside them.
>
> Persona Graph scrapes LinkedIn KOLs, subreddits, and X handles for a target persona — the **GTM Engineer**, in v1 — and renders the data as a force-directed graph: KOLs in the outer ring, content in the middle, engagers around the edges, colored by topic and sized by ICP fit. The point: stop guessing what the persona consumes; look at it.

**Loom demo:** _coming once the build runs end-to-end — embed lands here_.

**Why the GTM Engineer persona?** Because if you're reading this README, you probably are one. You should see yourself on the graph.

---

## Quickstart

```bash
git clone https://github.com/<your-handle>/persona-graph
cd persona-graph
./scripts/setup.sh               # Python venv + npm install + chflags + init DB
source .venv/bin/activate
python scripts/generate_seed.py  # populate data/intel.db with synthetic content (committed seed reproducible)
npm run dev                      # http://localhost:3000
```

The SQLite seed is committed (`data/intel.db`) per Shawn Logan's Nexus Intel pattern, so the dashboard renders immediately after `setup.sh` — no scraping or LLM calls required for the demo path.

---

## What this is not

- **Not a customer-facing app.** Internal dashboard. No auth, no API, no database writes from the browser. Read-only graph over a committed SQLite.
- **Not a real scrape.** v1 ships with a synthetic seed for reproducibility + zero-cost-to-clone. Live Apify scrape path is documented in `docs/demo.md`.
- **Not multi-tenant.** One persona (GTM Engineer) in v1. Schema supports more; adding them is a config change.
- **Not real-time.** Scrapes are batch (weekly cron in production). The graph is a snapshot.

---

## Credits

- **SQLite-in-git data layer pattern** from [Shawn Logan's `gtm-coding-agent`](https://github.com/shawnla90/gtm-coding-agent), Nexus Intel chapter. Verbatim borrow: the DB itself is committed, `git log data/intel.db` is the audit trail.
- **Apify CLI scraper pattern** (`apify call <actor-id> --input <json>`) — same source. Specific actors per Shawn's research: `harvestapi` (LinkedIn), `apidojo/tweet-scraper` (X), `trudax/reddit-scraper-lite` (Reddit).
- **4-dimension ICP scoring** from [gooseworks-ai/goose-skills](https://github.com/gooseworks-ai/goose-skills) → `icp-persona-builder` + `champion-tracker`.
- **Pain-language signal taxonomy** from gooseworks-ai/goose-skills → `pain-language-engagers`.
- **Sibling-repo conventions** (macOS chflags, `DRY_RUN=1` default, slash-command-first, dark-theme design system) from [reply-guy](https://github.com/ryanmichaels-jpg/reply-guy), [signal-catcher](https://github.com/ryanmichaels-jpg/signal-catcher), [cleanroom](https://github.com/ryanmichaels-jpg/cleanroom), [pipeline-resurrection](https://github.com/ryanmichaels-jpg/pipeline-resurrection).
