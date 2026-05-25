// TypeScript types matching scripts/export_graph_data.py output.
// Change this in sync with src/persona_graph/export.py.

export type NodeType = "source" | "content" | "engager";

export interface BaseNode {
  id: string;
  type: NodeType;
  label: string;
  color: string;
  size: number;
}

export interface SourceNode extends BaseNode {
  type: "source";
  platform: "linkedin" | "reddit" | "twitter";
  follower_count: number | null;
  content_count: number;
}

export interface ContentNode extends BaseNode {
  type: "content";
  full_text: string;
  source_id: string;
  engagement: number;
  age_days: number;
  topic_ids: string[];
  signal_ids: string[];
  primary_topic_id: string | null;
  is_hero?: boolean;
}

export interface EngagerNode extends BaseNode {
  type: "engager";
  company: string | null;
  title: string | null;
  company_size: number | null;
  platform: string | null;
  icp_score: number;
  tier: "tier_1" | "tier_2" | "tier_3" | "not_icp";
  score_breakdown: {
    b2b: number | null;
    seniority: number | null;
    company_size: number | null;
    gtm_relevance: number | null;
  };
}

export type GraphNode = SourceNode | ContentNode | EngagerNode;

export interface GraphEdge {
  source: string;
  target: string;
  type: "authored" | "engaged";
  weight: number;
  engagement_type?: "reaction" | "comment" | "repost";
}

export interface Topic {
  id: string;
  name: string;
  color: string;
  content_count: number;
}

export interface Signal {
  id: string;
  name: string;
  signal_type: "pain" | "buying" | "tool_mention";
  content_count: number;
}

export interface GraphData {
  persona: { id: string; name: string; description: string };
  topics: Topic[];
  signals: Signal[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    n_sources: number;
    n_content_items: number;
    n_engagers: number;
    n_topics: number;
    n_signals: number;
    n_engagements: number;
    tier_distribution: Record<string, number>;
    tier_colors: Record<string, string>;
  };
}
