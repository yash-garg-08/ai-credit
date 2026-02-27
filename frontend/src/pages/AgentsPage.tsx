import { useEffect, useMemo, useState } from "react";
import {
  agentGroupsApi,
  agentsApi,
  apiKeysApi,
  budgetsApi,
  credentialsApi,
  gatewayApi,
  orgsApi,
  policiesApi,
  workspacesApi,
} from "../api";
import type {
  Agent,
  AgentGroup,
  ApiKey,
  BudgetPeriod,
  CredentialMode,
  GatewayResponse,
  Organization,
  Workspace,
} from "../types";

type TargetLevel = "org" | "workspace" | "agent_group" | "agent";

function resolveTarget(
  level: TargetLevel,
  selectedOrg: Organization | null,
  selectedWs: Workspace | null,
  selectedGroup: AgentGroup | null,
  selectedAgent: Agent | null
): Record<string, string> | null {
  if (level === "org" && selectedOrg) return { org_id: selectedOrg.id };
  if (level === "workspace" && selectedWs) return { workspace_id: selectedWs.id };
  if (level === "agent_group" && selectedGroup) return { agent_group_id: selectedGroup.id };
  if (level === "agent" && selectedAgent) return { agent_id: selectedAgent.id };
  return null;
}

function parseIntOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function AgentsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWs, setSelectedWs] = useState<Workspace | null>(null);
  const [agentGroups, setAgentGroups] = useState<AgentGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<AgentGroup | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [newKey, setNewKey] = useState<ApiKey | null>(null);
  const [orgBalance, setOrgBalance] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Create forms
  const [orgName, setOrgName] = useState("");
  const [wsName, setWsName] = useState("");
  const [groupName, setGroupName] = useState("");
  const [agentName, setAgentName] = useState("");
  const [keyName, setKeyName] = useState("default");

  // Credential form
  const [credentialProvider, setCredentialProvider] = useState("openai");
  const [credentialKey, setCredentialKey] = useState("");
  const [credentialLabel, setCredentialLabel] = useState("");
  const [credentialMode, setCredentialMode] = useState<CredentialMode>("BYOK");

  // Policy form
  const [policyName, setPolicyName] = useState("Default Policy");
  const [policyTarget, setPolicyTarget] = useState<TargetLevel>("agent");
  const [policyAllowedModels, setPolicyAllowedModels] = useState("mock-model");
  const [policyMaxOutput, setPolicyMaxOutput] = useState("1024");
  const [policyRpm, setPolicyRpm] = useState("");

  // Budget form
  const [budgetTarget, setBudgetTarget] = useState<TargetLevel>("agent");
  const [budgetPeriod, setBudgetPeriod] = useState<BudgetPeriod>("DAILY");
  const [budgetLimit, setBudgetLimit] = useState("1000");
  const [budgetAutoDisable, setBudgetAutoDisable] = useState(true);

  const targetAvailability = useMemo(
    () => ({
      org: !!selectedOrg,
      workspace: !!selectedWs,
      agent_group: !!selectedGroup,
      agent: !!selectedAgent,
    }),
    [selectedOrg, selectedWs, selectedGroup, selectedAgent]
  );

  const loadOrgs = async () => {
    try {
      const data = await orgsApi.list();
      setOrgs(data);
      setSelectedOrg((prev) => prev ?? data[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load organizations");
    }
  };

  const loadAgents = async (agentGroupId: string) => {
    const data = await agentsApi.list(agentGroupId);
    setAgents(data);
    setSelectedAgent(data[0] ?? null);
  };

  useEffect(() => {
    loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrg) return;
    orgsApi.balance(selectedOrg.id).then((res) => setOrgBalance(res.balance)).catch(() => {});
    workspacesApi.list(selectedOrg.id).then((data) => {
      setWorkspaces(data);
      setSelectedWs(data[0] ?? null);
    });
  }, [selectedOrg]);

  useEffect(() => {
    if (!selectedWs) return;
    agentGroupsApi.list(selectedWs.id).then((data) => {
      setAgentGroups(data);
      setSelectedGroup(data[0] ?? null);
    });
  }, [selectedWs]);

  useEffect(() => {
    if (!selectedGroup) return;
    loadAgents(selectedGroup.id);
  }, [selectedGroup]);

  const createOrg = async () => {
    if (!orgName.trim()) return;
    try {
      await orgsApi.create(orgName.trim());
      setOrgName("");
      setNotice("Organization created");
      await loadOrgs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create organization");
    }
  };

  const createWs = async () => {
    if (!wsName.trim() || !selectedOrg) return;
    try {
      const ws = await workspacesApi.create(selectedOrg.id, wsName.trim());
      setWsName("");
      setWorkspaces((prev) => [...prev, ws]);
      setSelectedWs(ws);
      setNotice("Workspace created");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create workspace");
    }
  };

  const createGroup = async () => {
    if (!groupName.trim() || !selectedWs) return;
    try {
      const ag = await agentGroupsApi.create(selectedWs.id, groupName.trim());
      setGroupName("");
      setAgentGroups((prev) => [...prev, ag]);
      setSelectedGroup(ag);
      setNotice("Agent group created");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create agent group");
    }
  };

  const createAgent = async () => {
    if (!agentName.trim() || !selectedGroup) return;
    try {
      const a = await agentsApi.create(selectedGroup.id, agentName.trim());
      setAgentName("");
      setAgents((prev) => [...prev, a]);
      setSelectedAgent(a);
      setNotice("Agent created");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create agent");
    }
  };

  const issueKey = async (agentId: string) => {
    try {
      const key = await apiKeysApi.create(agentId, keyName || "default");
      setNewKey(key);
      setNotice("API key issued. Copy it now.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to issue API key");
    }
  };

  const createCredential = async () => {
    if (!selectedOrg || !credentialProvider.trim() || !credentialKey.trim()) return;
    try {
      await credentialsApi.create(
        selectedOrg.id,
        credentialProvider.trim(),
        credentialKey.trim(),
        credentialLabel.trim() || undefined,
        credentialMode
      );
      setCredentialKey("");
      setCredentialLabel("");
      setNotice("Credential saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save credential");
    }
  };

  const createPolicy = async () => {
    const target = resolveTarget(
      policyTarget,
      selectedOrg,
      selectedWs,
      selectedGroup,
      selectedAgent
    );
    if (!target) {
      setError("Selected policy target is not available.");
      return;
    }

    const allowedModels = policyAllowedModels
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean);

    try {
      await policiesApi.create({
        name: policyName.trim() || "Policy",
        ...target,
        allowed_models: allowedModels.length > 0 ? allowedModels : null,
        max_output_tokens: parseIntOrNull(policyMaxOutput),
        rpm_limit: parseIntOrNull(policyRpm),
      } as any);
      setNotice("Policy created");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create policy");
    }
  };

  const createBudget = async () => {
    const target = resolveTarget(
      budgetTarget,
      selectedOrg,
      selectedWs,
      selectedGroup,
      selectedAgent
    );
    if (!target) {
      setError("Selected budget target is not available.");
      return;
    }

    const limit = parseIntOrNull(budgetLimit);
    if (limit === null || limit <= 0) {
      setError("Budget limit must be a positive number.");
      return;
    }

    try {
      await budgetsApi.create({
        ...target,
        period: budgetPeriod,
        limit_credits: limit,
        auto_disable: budgetAutoDisable,
      } as any);
      setNotice("Budget created");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create budget");
    }
  };

  const statusBadge = (status: Agent["status"]) => {
    const colors = {
      ACTIVE: "bg-green-100 text-green-800",
      DISABLED: "bg-gray-100 text-gray-600",
      BUDGET_EXHAUSTED: "bg-red-100 text-red-700",
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[status]}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Governance</h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage hierarchy, credentials, policies, budgets, and run gateway tests
          </p>
        </div>
        <div className="text-sm text-gray-500">
          Org balance:{" "}
          <span className="font-semibold text-gray-800">
            {orgBalance !== null ? `${orgBalance.toLocaleString()} credits` : "—"}
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}
      {notice && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">
          {notice}
          <button onClick={() => setNotice(null)} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {newKey?.plaintext_key && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
          <p className="text-amber-800 font-semibold text-sm mb-2">
            New API key (shown once)
          </p>
          <code className="block bg-white border border-amber-200 rounded p-3 text-sm font-mono break-all select-all">
            {newKey.plaintext_key}
          </code>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="space-y-5">
          <Panel title="Organizations">
            <div className="flex gap-2 mb-3">
              <input
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createOrg()}
                placeholder="New org name"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={createOrg}
                className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create
              </button>
            </div>
            <div className="space-y-1 max-h-44 overflow-y-auto">
              {orgs.map((org) => (
                <button
                  key={org.id}
                  onClick={() => {
                    setSelectedOrg(org);
                    setSelectedWs(null);
                    setSelectedGroup(null);
                    setSelectedAgent(null);
                  }}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg ${
                    selectedOrg?.id === org.id
                      ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {org.name}
                  <span className="text-xs text-gray-400 ml-2">/{org.slug}</span>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title={`Workspaces${selectedOrg ? ` in ${selectedOrg.name}` : ""}`}>
            <div className="flex gap-2 mb-3">
              <input
                value={wsName}
                onChange={(e) => setWsName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createWs()}
                placeholder="New workspace"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={createWs}
                disabled={!selectedOrg}
                className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create
              </button>
            </div>
            <div className="space-y-1 max-h-44 overflow-y-auto">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => {
                    setSelectedWs(ws);
                    setSelectedGroup(null);
                    setSelectedAgent(null);
                  }}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg ${
                    selectedWs?.id === ws.id
                      ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {ws.name}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title={`Agent Groups${selectedWs ? ` in ${selectedWs.name}` : ""}`}>
            <div className="flex gap-2 mb-3">
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createGroup()}
                placeholder="New agent group"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={createGroup}
                disabled={!selectedWs}
                className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create
              </button>
            </div>
            <div className="space-y-1 max-h-44 overflow-y-auto">
              {agentGroups.map((ag) => (
                <button
                  key={ag.id}
                  onClick={() => {
                    setSelectedGroup(ag);
                    setSelectedAgent(null);
                  }}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg ${
                    selectedGroup?.id === ag.id
                      ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {ag.name}
                </button>
              ))}
            </div>
          </Panel>
        </section>

        <section className="space-y-5">
          <Panel title={`Agents${selectedGroup ? ` in ${selectedGroup.name}` : ""}`}>
            <div className="flex gap-2 mb-3">
              <input
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createAgent()}
                placeholder="New agent name"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={createAgent}
                disabled={!selectedGroup}
                className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create
              </button>
            </div>
            <div className="space-y-3">
              {agents.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">No agents yet</p>
              )}
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className={`border rounded-lg p-4 space-y-3 ${
                    selectedAgent?.id === agent.id
                      ? "border-blue-300 bg-blue-50/30"
                      : "border-gray-100"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setSelectedAgent(agent)}
                      className="font-medium text-sm text-gray-800 text-left hover:text-blue-700"
                    >
                      {agent.name}
                    </button>
                    {statusBadge(agent.status)}
                  </div>
                  <p className="text-xs text-gray-400 font-mono">{agent.id}</p>
                  <div className="flex gap-2">
                    <input
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      placeholder="Key label"
                      className="flex-1 text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                    />
                    <button
                      onClick={() => issueKey(agent.id)}
                      className="text-xs px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                      Issue API Key
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Provider Credentials">
            <div className="grid grid-cols-2 gap-2">
              <input
                value={credentialProvider}
                onChange={(e) => setCredentialProvider(e.target.value)}
                placeholder="Provider (openai/anthropic)"
                className="text-sm border border-gray-300 rounded-lg px-3 py-2"
              />
              <select
                value={credentialMode}
                onChange={(e) => setCredentialMode(e.target.value as CredentialMode)}
                className="text-sm border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value="BYOK">BYOK</option>
                <option value="MANAGED">MANAGED</option>
              </select>
            </div>
            <input
              value={credentialKey}
              onChange={(e) => setCredentialKey(e.target.value)}
              placeholder="Provider API key"
              className="mt-2 w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
            />
            <input
              value={credentialLabel}
              onChange={(e) => setCredentialLabel(e.target.value)}
              placeholder="Label (optional)"
              className="mt-2 w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
            />
            <button
              onClick={createCredential}
              disabled={!selectedOrg || !credentialKey.trim()}
              className="mt-3 w-full py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              Save Credential
            </button>
          </Panel>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Panel title="Create Policy">
              <select
                value={policyTarget}
                onChange={(e) => setPolicyTarget(e.target.value as TargetLevel)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              >
                <option value="org" disabled={!targetAvailability.org}>
                  Organization
                </option>
                <option value="workspace" disabled={!targetAvailability.workspace}>
                  Workspace
                </option>
                <option value="agent_group" disabled={!targetAvailability.agent_group}>
                  Agent Group
                </option>
                <option value="agent" disabled={!targetAvailability.agent}>
                  Agent
                </option>
              </select>
              <input
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                placeholder="Policy name"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              />
              <input
                value={policyAllowedModels}
                onChange={(e) => setPolicyAllowedModels(e.target.value)}
                placeholder="Allowed models (comma separated)"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              />
              <input
                value={policyMaxOutput}
                onChange={(e) => setPolicyMaxOutput(e.target.value)}
                placeholder="Max output tokens"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              />
              <input
                value={policyRpm}
                onChange={(e) => setPolicyRpm(e.target.value)}
                placeholder="RPM limit (optional)"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
              />
              <button
                onClick={createPolicy}
                className="mt-3 w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
              >
                Create Policy
              </button>
            </Panel>

            <Panel title="Create Budget">
              <select
                value={budgetTarget}
                onChange={(e) => setBudgetTarget(e.target.value as TargetLevel)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              >
                <option value="org" disabled={!targetAvailability.org}>
                  Organization
                </option>
                <option value="workspace" disabled={!targetAvailability.workspace}>
                  Workspace
                </option>
                <option value="agent_group" disabled={!targetAvailability.agent_group}>
                  Agent Group
                </option>
                <option value="agent" disabled={!targetAvailability.agent}>
                  Agent
                </option>
              </select>
              <select
                value={budgetPeriod}
                onChange={(e) => setBudgetPeriod(e.target.value as BudgetPeriod)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              >
                <option value="DAILY">DAILY</option>
                <option value="MONTHLY">MONTHLY</option>
                <option value="TOTAL">TOTAL</option>
              </select>
              <input
                value={budgetLimit}
                onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder="Limit credits"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              />
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={budgetAutoDisable}
                  onChange={(e) => setBudgetAutoDisable(e.target.checked)}
                />
                Auto-disable target on exceed
              </label>
              <button
                onClick={createBudget}
                className="mt-3 w-full py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700"
              >
                Create Budget
              </button>
            </Panel>
          </div>
        </section>
      </div>

      <GatewayTest initialApiKey={newKey?.plaintext_key} />
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800 mb-3">{title}</h2>
      {children}
    </section>
  );
}

function GatewayTest({ initialApiKey }: { initialApiKey?: string }) {
  const [apiKey, setApiKey] = useState(initialApiKey ?? "");
  const [model, setModel] = useState("mock-model");
  const [message, setMessage] = useState("Hello! Tell me something interesting.");
  const [response, setResponse] = useState<string | null>(null);
  const [stats, setStats] = useState<{ credits: number; latency: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialApiKey) {
      setApiKey(initialApiKey);
    }
  }, [initialApiKey]);

  const sendRequest = async () => {
    if (!apiKey.trim()) {
      setError("Enter a cpk_ API key first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data: GatewayResponse = await gatewayApi.chat(apiKey.trim(), model, [
        { role: "user", content: message },
      ]);
      setResponse(data.choices[0]?.message?.content ?? "");
      setStats({
        credits: data.x_platform?.credits_charged ?? 0,
        latency: data.x_platform?.latency_ms ?? 0,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gateway error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Gateway Test</h2>
      <div className="space-y-3">
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="cpk_... API key"
          className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
        />
        <input
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="Model (gpt-4o-mini, claude-..., mock-model)"
          className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
        />
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="Your message"
          className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 resize-none"
        />
        <button
          onClick={sendRequest}
          disabled={loading}
          className="w-full py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Sending..." : "Send via Gateway"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {response !== null && (
          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-800 whitespace-pre-wrap">
            {response}
          </div>
        )}
        {stats && (
          <div className="flex gap-4 text-xs text-gray-500">
            <span>
              Credits charged: <strong className="text-gray-700">{stats.credits}</strong>
            </span>
            <span>
              Latency: <strong className="text-gray-700">{stats.latency}ms</strong>
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
