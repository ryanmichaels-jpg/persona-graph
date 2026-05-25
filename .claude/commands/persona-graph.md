---
description: Rebuild the persona graph (seed → analyze → score → export) and open the dashboard
argument-hint: [--live] [--no-open]
---

You are rebuilding the Persona Graph end-to-end. `$ARGUMENTS` controls live vs dry-run + whether to open the browser.

## Parse flags

- `--live` → use Claude Haiku 4.5 for content tagging + Sonnet 4.6 for the dashboard narrative (needs `ANTHROPIC_API_KEY` in `.env`)
- `--no-open` → skip opening the dev server in the browser

Default: dry-run (keyword tagger), open dashboard at the end.

## Run the pipeline

Use `Bash` from the repo root. Use `.venv/bin/python` if it exists, else `python`.

1. **Seed**:  `.venv/bin/python scripts/generate_seed.py`
2. **Analyze**: `.venv/bin/python scripts/analyze_content.py {{LIVE_FLAG}}`
3. **Score**:   `.venv/bin/python scripts/score_engagers.py`
4. **Export**:  `.venv/bin/python scripts/export_graph_data.py`
5. If `--no-open` is NOT set: start `npm run dev` in the background and tell the user to open `http://localhost:3000`.

`{{LIVE_FLAG}}` = `--live` when the user passed `--live`, else empty.

## Tell the user what happened

After the pipeline runs, summarize from the export output:
- N content items tagged
- Tier distribution: tier_1 / tier_2 / tier_3 / not_icp
- Topic distribution (top 3)
- Top 3 pain signals by content count
- The top 3 engagers by ICP score (call them out by name)
- Dashboard URL if running

## Guardrails

- Don't run Apify live scrapes from this command — that's a separate `scripts/run_apify_scrape.py` (not built yet in v1).
- Don't commit anything; this is local dev.
- If `--live` is set but `ANTHROPIC_API_KEY` is missing, warn and fall back to dry-run.
