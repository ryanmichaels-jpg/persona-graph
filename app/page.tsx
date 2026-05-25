import fs from "node:fs/promises";
import path from "node:path";
import { PersonaGraphView } from "@/components/PersonaGraph";
import type { GraphData, EngagerNode } from "@/lib/data";

async function loadGraph(): Promise<GraphData> {
  const p = path.join(process.cwd(), "data", "graph.json");
  const txt = await fs.readFile(p, "utf8");
  return JSON.parse(txt) as GraphData;
}

export default async function Page() {
  const data = await loadGraph();
  const persona = data.persona;
  const stats = data.stats;
  const tier1 = stats.tier_distribution["tier_1"] ?? 0;
  const tier2 = stats.tier_distribution["tier_2"] ?? 0;
  const engagers = data.nodes.filter((n): n is EngagerNode => n.type === "engager");
  const topEngagers = engagers
    .slice()
    .sort((a, b) => b.icp_score - a.icp_score)
    .slice(0, 12);

  const tierColors = stats.tier_colors;

  return (
    <div className="wrap">
      <h1>Persona Graph — {persona.name}</h1>
      <p className="subtitle">
        {data.nodes.filter((n) => n.type === "source").length} content sources · {" "}
        {data.nodes.filter((n) => n.type === "content").length} content items · {" "}
        {engagers.length} engagers · synthetic seed (gitignore-free, reproducible)
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Content sources</div>
          <div className="big">{stats.n_sources}</div>
          <div className="delta">5 LinkedIn · 3 Reddit · 2 X handles</div>
        </div>
        <div className="stat-card">
          <div className="label">Content items</div>
          <div className="big">{stats.n_content_items}</div>
          <div className="delta">{data.nodes.filter((n) => n.type === "content" && (n as any).is_hero).length} hero posts seeded</div>
        </div>
        <div className="stat-card">
          <div className="label">Engagers</div>
          <div className="big">{stats.n_engagers}</div>
          <div className="delta">{stats.n_engagements} engagements tracked</div>
        </div>
        <div className="stat-card">
          <div className="label">Tier 1 / Tier 2</div>
          <div className="big" style={{ color: tierColors["tier_1"] }}>
            {tier1}<span style={{ color: "var(--dim)", fontSize: 18 }}> / </span>
            <span style={{ color: tierColors["tier_2"] }}>{tier2}</span>
          </div>
          <div className="delta">strong-fit / adjacent engagers</div>
        </div>
      </div>

      <div className="main-grid">
        <div>
          <PersonaGraphView data={data} />
        </div>
        <div>
          <h2 style={{ marginTop: 0 }}>Legend</h2>
          <div className="panel">
            <div className="legend-row" style={{ cursor: "default" }}>
              <div className="swatch" style={{ background: "#ec4899" }} />
              <div className="name">Source (KOL / subreddit)</div>
              <div className="count">{stats.n_sources}</div>
            </div>
            <div className="legend-row" style={{ cursor: "default" }}>
              <div className="swatch" style={{ background: "#94a3b8", border: "1px solid #fff" }} />
              <div className="name">Content (★ = hero post)</div>
              <div className="count">{stats.n_content_items}</div>
            </div>
            <div className="legend-row" style={{ cursor: "default" }}>
              <div className="swatch" style={{ background: tierColors["tier_1"] }} />
              <div className="name">Engager · Tier 1</div>
              <div className="count">{tier1}</div>
            </div>
            <div className="legend-row" style={{ cursor: "default" }}>
              <div className="swatch" style={{ background: tierColors["tier_2"] }} />
              <div className="name">Engager · Tier 2</div>
              <div className="count">{tier2}</div>
            </div>
            <div className="legend-row" style={{ cursor: "default" }}>
              <div className="swatch" style={{ background: tierColors["tier_3"] }} />
              <div className="name">Engager · Tier 3</div>
              <div className="count">{stats.tier_distribution["tier_3"] ?? 0}</div>
            </div>
          </div>

          <h2>Pain signals</h2>
          <div className="panel">
            {data.signals.filter((s) => s.signal_type === "pain").map((s) => (
              <div key={s.id} className="legend-row" style={{ cursor: "default" }}>
                <div className="swatch" style={{ background: "var(--red)" }} />
                <div className="name">{s.name}</div>
                <div className="count">{s.content_count}</div>
              </div>
            ))}
          </div>

          <h2>Buying signals</h2>
          <div className="panel">
            {data.signals.filter((s) => s.signal_type === "buying").map((s) => (
              <div key={s.id} className="legend-row" style={{ cursor: "default" }}>
                <div className="swatch" style={{ background: "var(--green)" }} />
                <div className="name">{s.name}</div>
                <div className="count">{s.content_count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <h2>Top engagers by ICP score</h2>
      <div className="panel">
        <table className="engagers">
          <thead>
            <tr>
              <th>Name</th><th>Title</th><th>Company</th><th>Size</th>
              <th>Tier</th><th className="score">ICP score</th>
            </tr>
          </thead>
          <tbody>
            {topEngagers.map((e) => (
              <tr key={e.id} className={e.tier}>
                <td>{e.label}</td>
                <td>{e.title}</td>
                <td>{e.company}</td>
                <td>{e.company_size}</td>
                <td className="tier">{e.tier}</td>
                <td className="score">{e.icp_score.toFixed(2)} / 4</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer>
        Persona Graph · GTM Engineer · SQLite-in-git data layer borrowed verbatim from{" "}
        <a href="https://github.com/shawnla90/gtm-coding-agent">Shawn Logan&apos;s Nexus Intel</a>.
        Synthetic seed for the demo; live Apify scrape path documented in <code>docs/demo.md</code>.
      </footer>
    </div>
  );
}
