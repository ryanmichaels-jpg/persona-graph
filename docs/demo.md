# Persona Graph — Demo guide

The 2-minute Loom storyline + how to wire up live Apify scraping (optional polish).

---

## 2-minute Loom flow

| Time      | Show                                                                                          |
|-----------|-----------------------------------------------------------------------------------------------|
| 0:00–0:15 | `cat src/persona_graph/seed/seed_config.yaml \| head -30`. Voiceover: "I built a graph of the GTM Engineer persona. Who they follow, what they post, what they complain about. The point: you should see yourself on this graph." |
| 0:15–0:30 | `npm run dev`. Browser opens. Show the dashboard top: persona description + 4 stat cards (10 sources / 80 posts / 40 engagers / 32+7 tier 1+2). |
| 0:30–1:15 | Scroll to the graph. Hover a few hero post nodes (white-ringed): point at the "Just shipped a stale-deal scanner" post, the "RevOps in 2026 is just LLM glue code" Reddit thread, the "Hiring our first GTM Engineer" tweet. Voiceover: "These are real engagement patterns — content with the highest pull. The pink nodes are sources, color in the middle is topic, color around the edges is ICP tier." |
| 1:15–1:45 | Click a topic in the right sidebar (e.g. "RevOps automation") to dim non-matching content. Show the graph reshape. "Filter the persona by what they actually complain about." |
| 1:45–2:00 | Scroll to "Top engagers by ICP score" table. Show 12 highest-scoring engagers — most are GTM Engineers + RevOps managers, exactly the persona definition. Close on the README's credit line for Shawn Logan's Nexus Intel. |

Total wall-clock: ~2 min. Edit at 1.5x.

---

## Run the dashboard (dry-run, no credentials)

```bash
git clone https://github.com/ryanmichaels-jpg/persona-graph
cd persona-graph
./scripts/setup.sh                           # Python venv + npm install + chflags + init DB
source .venv/bin/activate
python scripts/generate_seed.py              # populate data/intel.db (synthetic GTM-engineer corpus)
python scripts/analyze_content.py            # keyword-tag topics + signals (no LLM in dry-run)
python scripts/score_engagers.py             # 4-dim ICP score per engager
python scripts/export_graph_data.py          # data/intel.db → data/graph.json
npm run dev                                  # open http://localhost:3000
```

Expected:
- All four Python stages finish in < 5 seconds.
- `npm run dev` boots in ~3 seconds; first page load < 1 second.
- Dashboard renders the graph with hero posts (white-ringed) visible.

The full re-build is also wrapped in the slash command: `/persona-graph`.

---

## Live mode (real Claude tagging)

```bash
# Set ANTHROPIC_API_KEY in .env first
python scripts/analyze_content.py --live
python scripts/score_engagers.py
python scripts/export_graph_data.py
npm run dev
```

What `--live` changes:
- `analyze_content.py` uses **Claude Haiku 4.5** instead of keyword scan. Better recall on subtle pain language, mentions, and buying signals. ~$0.005 per content item; <$0.50 for the full 80-item corpus.

ICP scoring + export stay deterministic regardless of `--live`.

---

## Live scrape (real Apify, optional polish)

Not built into v1; here's the path if you want to wire it up.

### 1. Install Apify CLI

```bash
npm install -g apify-cli
apify login                                  # opens browser, paste your API token
```

### 2. Set `APIFY_API_TOKEN` in `.env`

### 3. Add a scrape script

The Apify actors per Shawn's research:
- `harvestapi/linkedin-profile-posts` — for LinkedIn KOL posts
- `apidojo/tweet-scraper` — for X handles
- `trudax/reddit-scraper-lite` — for subreddit threads

A scrape script would call `apify call <actor-id> --input <json>` for each source, parse the JSON output, and INSERT OR IGNORE into the `content_items` + `engagers` tables.

Cost: ~$3 per fresh scrape across all 10 sources. The committed seed pattern means you only need to scrape when you want fresh data — re-running the demo doesn't require a new scrape.

---

## Railway deploy (optional polish)

The dashboard ships as a Next.js static + server component. Railway can host it directly:

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Set `INTEL_DB_PATH` env var on Railway if you want it to read from a non-default location. The committed `data/intel.db` + `data/graph.json` will be deployed as-is — set `INTEL_DB_WRITABLE=0` so any background scrape jobs know not to write to prod.

Not done in v1; local + Loom screenshot is enough for the portfolio demo.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'persona_graph'`** — macOS gotcha. Re-run `./scripts/setup.sh` (clears `UF_HIDDEN` on `.venv/.../*.pth`).

**`npm error EACCES ... /Users/<you>/.npm`** — root-owned files in your npm cache. Either run `sudo chown -R $(id -u):$(id -g) ~/.npm`, or use `npm install --cache /tmp/npm-cache-persona-graph` to bypass.

**`gyp: command not found`** — would only happen if you re-add `better-sqlite3` to package.json. v1 doesn't use it; the JSON-snapshot pattern avoids node-gyp entirely.

**Dashboard shows empty graph** — `data/graph.json` is missing or stale. Re-run `python scripts/export_graph_data.py`.

**Hero posts not visible** — the seed wasn't regenerated. Run `python scripts/generate_seed.py` before `export_graph_data.py`.
