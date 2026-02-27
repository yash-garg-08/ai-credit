import type {
  Agent,
  AgentGroup,
  ApiKey,
  BalanceResponse,
  Budget,
  BudgetPeriod,
  BurnRate,
  Credential,
  CredentialMode,
  GatewayResponse,
  Group,
  LedgerEntry,
  Organization,
  Policy,
  PricingRule,
  TopUser,
  UsageEvent,
  UsageResponse,
  User,
  Workspace,
} from "./types";

const BASE = "/api";

function getToken(): string {
  return localStorage.getItem("token") ?? "";
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// --- Auth ---
export const authApi = {
  register: (email: string, password: string) =>
    request<User>("POST", "/auth/register", { email, password }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("POST", "/auth/login", {
      email,
      password,
    }),
};

// --- Groups (legacy) ---
export const groupsApi = {
  myGroups: () => request<Group[]>("GET", "/groups/me"),
  create: (name: string) => request<Group>("POST", "/groups", { name }),
  invite: (groupId: string, email: string, role: "ADMIN" | "MEMBER" = "MEMBER") =>
    request("POST", `/groups/${groupId}/invite`, { email, role }),
  balance: (groupId: string) =>
    request<BalanceResponse>("GET", `/groups/${groupId}/balance`),
};

// --- Credits ---
export const creditsApi = {
  purchase: (groupId: string, amount: number, idempotencyKey?: string) =>
    request<LedgerEntry>("POST", "/credits/purchase", {
      group_id: groupId,
      amount,
      idempotency_key: idempotencyKey ?? `purchase-${Date.now()}`,
    }),
};

// --- Usage ---
export const usageApi = {
  request: (groupId: string, provider: string, model: string, message: string) =>
    request<UsageResponse>("POST", "/usage/request", {
      group_id: groupId,
      provider,
      model,
      messages: [{ role: "user", content: message }],
      request_id: crypto.randomUUID(),
    }),
  history: (groupId: string, limit = 20, offset = 0) =>
    request<UsageEvent[]>("GET", `/usage/history/${groupId}?limit=${limit}&offset=${offset}`),
  burnRate: (groupId: string) =>
    request<BurnRate>("GET", `/usage/burn-rate/${groupId}`),
  topUsers: (groupId: string) =>
    request<TopUser[]>("GET", `/usage/top-users/${groupId}`),
};

// --- Pricing ---
export const pricingApi = {
  list: () => request<PricingRule[]>("GET", "/pricing"),
};

// ── Multi-tenant governance APIs ──────────────────────────────────────────────

// --- Organizations ---
export const orgsApi = {
  list: () => request<Organization[]>("GET", "/orgs"),
  create: (name: string, description?: string) =>
    request<Organization>("POST", "/orgs", { name, description }),
  balance: (orgId: string) =>
    request<{ org_id: string; balance: number }>("GET", `/orgs/${orgId}/balance`),
};

// --- Workspaces ---
export const workspacesApi = {
  list: (orgId: string) =>
    request<Workspace[]>("GET", `/orgs/${orgId}/workspaces`),
  create: (orgId: string, name: string, description?: string) =>
    request<Workspace>("POST", `/orgs/${orgId}/workspaces`, { name, description }),
};

// --- Agent Groups ---
export const agentGroupsApi = {
  list: (workspaceId: string) =>
    request<AgentGroup[]>("GET", `/workspaces/${workspaceId}/agent-groups`),
  create: (workspaceId: string, name: string, description?: string) =>
    request<AgentGroup>("POST", `/workspaces/${workspaceId}/agent-groups`, { name, description }),
};

// --- Agents ---
export const agentsApi = {
  list: (agentGroupId: string) =>
    request<Agent[]>("GET", `/agent-groups/${agentGroupId}/agents`),
  create: (agentGroupId: string, name: string, description?: string) =>
    request<Agent>("POST", `/agent-groups/${agentGroupId}/agents`, { name, description }),
};

// --- API Keys ---
export const apiKeysApi = {
  list: (agentId: string) =>
    request<ApiKey[]>("GET", `/agents/${agentId}/keys`),
  create: (agentId: string, name: string) =>
    request<ApiKey>("POST", `/agents/${agentId}/keys`, { name }),
  revoke: (agentId: string, keyId: string) =>
    request<void>("DELETE", `/agents/${agentId}/keys/${keyId}`),
};

// --- Credentials (BYOK / managed provider keys) ---
export const credentialsApi = {
  list: (orgId: string) =>
    request<Credential[]>("GET", `/orgs/${orgId}/credentials`),
  create: (
    orgId: string,
    provider: string,
    apiKey: string,
    label?: string,
    mode: CredentialMode = "BYOK"
  ) =>
    request<Credential>("POST", `/orgs/${orgId}/credentials`, {
      provider,
      api_key: apiKey,
      label,
      mode,
    }),
};

type PolicyCreatePayload = {
  name: string;
  allowed_models?: string[] | null;
  max_input_tokens?: number | null;
  max_output_tokens?: number | null;
  rpm_limit?: number | null;
  org_id?: string;
  workspace_id?: string;
  agent_group_id?: string;
  agent_id?: string;
};

export const policiesApi = {
  list: (params: {
    org_id?: string;
    workspace_id?: string;
    agent_group_id?: string;
    agent_id?: string;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => Boolean(value)) as Array<
        [string, string]
      >
    );
    return request<Policy[]>("GET", `/policies?${query.toString()}`);
  },
  create: (payload: PolicyCreatePayload) =>
    request<Policy>("POST", "/policies", payload),
};

type BudgetCreatePayload = {
  period: BudgetPeriod;
  limit_credits: number;
  auto_disable?: boolean;
  org_id?: string;
  workspace_id?: string;
  agent_group_id?: string;
  agent_id?: string;
};

export const budgetsApi = {
  list: (params: {
    org_id?: string;
    workspace_id?: string;
    agent_group_id?: string;
    agent_id?: string;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => Boolean(value)) as Array<
        [string, string]
      >
    );
    return request<Budget[]>("GET", `/budgets?${query.toString()}`);
  },
  create: (payload: BudgetCreatePayload) =>
    request<Budget>("POST", "/budgets", payload),
};

// --- Gateway (direct call with cpk_ key) ---
export const gatewayApi = {
  chat: (apiKey: string, model: string, messages: { role: string; content: string }[], maxTokens?: number) =>
    fetch(`${BASE}/gateway/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ model, messages, max_tokens: maxTokens }),
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Gateway error");
      }
      return res.json() as Promise<GatewayResponse>;
    }),
};
