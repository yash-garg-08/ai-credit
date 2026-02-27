export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Group {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface BalanceResponse {
  group_id: string;
  balance: number;
}

export interface LedgerEntry {
  id: string;
  group_id: string;
  amount: number;
  type: "CREDIT_PURCHASE" | "USAGE_DEDUCTION" | "ADJUSTMENT" | "REFUND";
  metadata_: Record<string, unknown> | null;
  created_at: string;
}

export interface UsageEvent {
  id: string;
  user_id: string;
  group_id: string;
  agent_id: string | null;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: string;
  credits_charged: number;
  latency_ms: number | null;
  status: "SUCCESS" | "ERROR" | "POLICY_BLOCKED" | "BUDGET_EXCEEDED";
  error_message: string | null;
  created_at: string;
}

export interface UsageResponse {
  request_id: string;
  response: string;
  input_tokens: number;
  output_tokens: number;
  credits_charged: number;
}

export interface BurnRate {
  group_id: string;
  credits_last_24h: number;
  credits_last_7d: number;
}

export interface TopUser {
  user_id: string;
  total_credits: number;
}

export interface PricingRule {
  id: string;
  provider: string;
  model: string;
  input_cost_per_1k: string;
  output_cost_per_1k: string;
  created_at: string;
}

export interface ApiError {
  detail: string;
}

// ── Multi-tenant governance types ─────────────────────────────────────────────

export interface Organization {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  billing_group_id: string;
  credits_per_usd: number;
  is_active: boolean;
  description: string | null;
  created_at: string;
}

export interface Workspace {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AgentGroup {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Agent {
  id: string;
  agent_group_id: string;
  name: string;
  description: string | null;
  status: "ACTIVE" | "DISABLED" | "BUDGET_EXHAUSTED";
  created_at: string;
}

export interface ApiKey {
  id: string;
  agent_id: string;
  name: string;
  key_suffix: string;
  is_active: boolean;
  created_at: string;
  plaintext_key?: string; // Only present at creation
}

export interface GatewayResponse {
  id: string;
  object: string;
  model: string;
  choices: {
    index: number;
    message: { role: string; content: string };
    finish_reason: string;
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  x_platform: {
    credits_charged: number;
    latency_ms: number;
    request_id: string;
  };
}
