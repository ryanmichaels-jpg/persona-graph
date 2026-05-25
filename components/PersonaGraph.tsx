"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import type { GraphData, GraphEdge, GraphNode } from "@/lib/data";

interface Props {
  data: GraphData;
  width?: number;
  height?: number;
}

type SimNode = GraphNode & SimulationNodeDatum;
type SimLink = SimulationLinkDatum<SimNode> & Omit<GraphEdge, "source" | "target">;

interface HoverState {
  node: SimNode;
  x: number;
  y: number;
}

export function PersonaGraphView({ data, width = 1040, height = 640 }: Props) {
  // ---- topic-filter toggle state -----------------------------------------
  const allTopicIds = useMemo(() => data.topics.map((t) => t.id), [data.topics]);
  const [activeTopics, setActiveTopics] = useState<Set<string>>(new Set(allTopicIds));

  function toggleTopic(id: string) {
    setActiveTopics((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  const allActive = activeTopics.size === allTopicIds.length;
  function showAll() { setActiveTopics(new Set(allTopicIds)); }

  // ---- d3-force simulation -----------------------------------------------
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [tick, setTick] = useState(0);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);

  // Clone nodes/edges into a stable simulation-bound array (once per data ref)
  const { simNodes, simLinks } = useMemo(() => {
    const ns: SimNode[] = data.nodes.map((n) => ({ ...n }));
    const idIndex = new Map(ns.map((n) => [n.id, n] as const));
    const ls: SimLink[] = [];
    for (const e of data.edges) {
      const s = idIndex.get(e.source);
      const t = idIndex.get(e.target);
      if (!s || !t) continue;
      const link: SimLink = {
        source: s,
        target: t,
        type: e.type,
        weight: e.weight,
        engagement_type: e.engagement_type,
      };
      ls.push(link);
    }
    return { simNodes: ns, simLinks: ls };
  }, [data]);

  useEffect(() => {
    const sim = forceSimulation<SimNode, SimLink>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance((l) => (l.type === "authored" ? 70 : 120))
          .strength(0.35),
      )
      .force("charge", forceManyBody().strength(-80))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide<SimNode>((n) => n.size + 3))
      .alpha(1)
      .alphaDecay(0.03);

    sim.on("tick", () => setTick((t) => t + 1));
    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [simNodes, simLinks, width, height]);

  // ---- hover state -------------------------------------------------------
  const [hover, setHover] = useState<HoverState | null>(null);
  function onNodeEnter(n: SimNode, ev: React.MouseEvent) {
    setHover({ node: n, x: ev.clientX, y: ev.clientY });
  }
  function onNodeMove(ev: React.MouseEvent) {
    setHover((h) => (h ? { ...h, x: ev.clientX, y: ev.clientY } : h));
  }
  function onNodeLeave() { setHover(null); }

  // ---- filter helper -----------------------------------------------------
  function isNodeActive(n: SimNode): boolean {
    if (allActive) return true;
    if (n.type !== "content") return true;
    const cn = n as Extract<GraphNode, { type: "content" }>;
    if (!cn.topic_ids || cn.topic_ids.length === 0) return false;
    return cn.topic_ids.some((t) => activeTopics.has(t));
  }

  // ---- render ------------------------------------------------------------
  void tick; // re-render trigger from sim

  return (
    <div>
      <div className="graph-container panel" onMouseMove={onNodeMove}>
        <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`}>
          {/* edges */}
          <g stroke="#2a2f3a" strokeOpacity={0.5}>
            {simLinks.map((l, i) => {
              const s = l.source as SimNode;
              const t = l.target as SimNode;
              if (s.x == null || t.x == null) return null;
              const active = isNodeActive(s) && isNodeActive(t);
              return (
                <line
                  key={i}
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  strokeOpacity={active ? (l.type === "authored" ? 0.4 : 0.18) : 0.05}
                  strokeWidth={l.type === "authored" ? 1.4 : 0.8}
                />
              );
            })}
          </g>
          {/* nodes */}
          <g>
            {simNodes.map((n) => {
              if (n.x == null || n.y == null) return null;
              const active = isNodeActive(n);
              const isHero = (n as Extract<GraphNode, { type: "content" }>).is_hero;
              return (
                <circle
                  key={n.id}
                  cx={n.x}
                  cy={n.y}
                  r={n.size}
                  fill={n.color}
                  fillOpacity={active ? (isHero ? 1 : 0.85) : 0.15}
                  stroke={isHero ? "#fff" : "transparent"}
                  strokeWidth={isHero ? 1.5 : 0}
                  onMouseEnter={(ev) => onNodeEnter(n, ev)}
                  onMouseLeave={onNodeLeave}
                  style={{ cursor: "pointer" }}
                />
              );
            })}
          </g>
        </svg>
      </div>

      {hover && <NodeTooltip hover={hover} />}

      <h2>Topic filter</h2>
      <div className="panel">
        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          <button className={allActive ? "active" : ""} onClick={showAll}>All topics</button>
        </div>
        {data.topics.map((t) => {
          const active = activeTopics.has(t.id);
          return (
            <div
              key={t.id}
              className={`legend-row ${active ? "" : "dimmed"}`}
              onClick={() => toggleTopic(t.id)}
            >
              <div className="swatch" style={{ background: t.color }} />
              <div className="name">{t.name}</div>
              <div className="count">{t.content_count}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}


function NodeTooltip({ hover }: { hover: HoverState }) {
  const n = hover.node;
  const x = Math.min(window.innerWidth - 360, hover.x + 14);
  const y = Math.min(window.innerHeight - 200, hover.y + 14);

  if (n.type === "source") {
    const sn = n as Extract<GraphNode, { type: "source" }>;
    return (
      <div className="tooltip" style={{ left: x, top: y }}>
        <div className="ttl">{sn.label}</div>
        <div>{sn.platform} · {sn.content_count} posts</div>
        {sn.follower_count != null && (
          <div className="meta">{sn.follower_count.toLocaleString()} followers</div>
        )}
      </div>
    );
  }
  if (n.type === "content") {
    const cn = n as Extract<GraphNode, { type: "content" }>;
    return (
      <div className="tooltip" style={{ left: x, top: y }}>
        <div className="ttl">{cn.is_hero ? "★ hero post" : "post"}</div>
        <div>{cn.full_text}</div>
        <div className="meta">
          {cn.engagement} engagements · {cn.age_days}d old · topics: {cn.topic_ids?.length ?? 0} · signals: {cn.signal_ids?.length ?? 0}
        </div>
      </div>
    );
  }
  const en = n as Extract<GraphNode, { type: "engager" }>;
  return (
    <div className="tooltip" style={{ left: x, top: y }}>
      <div className="ttl">{en.label}</div>
      <div>{en.title}{en.company ? ` @ ${en.company}` : ""}</div>
      <div className="meta">
        Tier <strong style={{ color: en.color }}>{en.tier}</strong> · ICP score {en.icp_score.toFixed(2)}/4
        {en.company_size != null && ` · ${en.company_size} employees`}
      </div>
    </div>
  );
}
