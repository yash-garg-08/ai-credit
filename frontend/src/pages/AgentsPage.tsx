import { useEffect, useState } from "react";
import { agentGroupsApi, agentsApi, apiKeysApi, orgsApi, workspacesApi } from "../api";
import type { Agent, AgentGroup, ApiKey, Organization, Workspace } from "../types";

export default function AgentsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWs, setSelectedWs] = useState<Workspace | null>(null);
  const [agentGroups, setAgentGroups] = useState<AgentGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<AgentGroup | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [newKey, setNewKey] = useState<ApiKey | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Create forms
  const [orgName, setOrgName] = useState("");
  const [wsName, setWsName] = useState("");
  const [groupName, setGroupName] = useState("");
  const [agentName, setAgentName] = useState("");
  const [keyName, setKeyName] = useState("default");

  const loadOrgs = async () => {
    try {
      const data = await orgsApi.list();
      setOrgs(data);
      if (data.length > 0 && !selectedOrg) {
        setSelectedOrg(data[0]);
      }
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => { loadOrgs(); }, []);

  useEffect(() => {
    if (!selectedOrg) return;
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
    agentsApi.list(selectedGroup.id).then(setAgents);
  }, [selectedGroup]);

  const createOrg = async () => {
    if (!orgName.trim()) return;
    try {
      await orgsApi.create(orgName.trim());
      setOrgName("");
      loadOrgs();
    } catch (e) { setError(String(e)); }
  };

  const createWs = async () => {
    if (!wsName.trim() || !selectedOrg) return;
    try {
      const ws = await workspacesApi.create(selectedOrg.id, wsName.trim());
      setWsName("");
      setWorkspaces((prev) => [...prev, ws]);
      setSelectedWs(ws);
    } catch (e) { setError(String(e)); }
  };

  const createGroup = async () => {
    if (!groupName.trim() || !selectedWs) return;
    try {
      const ag = await agentGroupsApi.create(selectedWs.id, groupName.trim());
      setGroupName("");
      setAgentGroups((prev) => [...prev, ag]);
      setSelectedGroup(ag);
    } catch (e) { setError(String(e)); }
  };

  const createAgent = async () => {
    if (!agentName.trim() || !selectedGroup) return;
    try {
      const a = await agentsApi.create(selectedGroup.id, agentName.trim());
      setAgentName("");
      setAgents((prev) => [...prev, a]);
    } catch (e) { setError(String(e)); }
  };

  const issueKey = async (agentId: string) => {
    try {
      const key = await apiKeysApi.create(agentId, keyName || "default");
      setNewKey(key);
    } catch (e) { setError(String(e)); }
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
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agent Governance</h1>
        <p className="text-gray-500 text-sm mt-1">
          Manage the Org → Workspace → AgentGroup → Agent hierarchy
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* New API key reveal */}
      {newKey?.plaintext_key && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
          <p className="text-amber-800 font-semibold text-sm mb-2">
            New API Key (copy now — shown only once)
          </p>
          <code className="block bg-white border border-amber-200 rounded p-3 text-sm font-mono break-all select-all">
            {newKey.plaintext_key}
          </code>
          <button
            onClick={() => { navigator.clipboard.writeText(newKey.plaintext_key!); }}
            className="mt-2 text-xs text-amber-700 underline hover:text-amber-900"
          >
            Copy to clipboard
          </button>
          <button
            onClick={() => setNewKey(null)}
            className="ml-4 text-xs text-amber-700 underline hover:text-amber-900"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column: hierarchy navigation */}
        <div className="space-y-5">
          {/* Organizations */}
          <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Organizations</h2>
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
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {orgs.map((org) => (
                <button
                  key={org.id}
                  onClick={() => { setSelectedOrg(org); setSelectedWs(null); setSelectedGroup(null); }}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${
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
          </section>

          {/* Workspaces */}
          {selectedOrg && (
            <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-800 mb-3">
                Workspaces <span className="text-gray-400 font-normal text-xs">in {selectedOrg.name}</span>
              </h2>
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
                  className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create
                </button>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => { setSelectedWs(ws); setSelectedGroup(null); }}
                    className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${
                      selectedWs?.id === ws.id
                        ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {ws.name}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Agent Groups */}
          {selectedWs && (
            <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-800 mb-3">
                Agent Groups <span className="text-gray-400 font-normal text-xs">in {selectedWs.name}</span>
              </h2>
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
                  className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create
                </button>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {agentGroups.map((ag) => (
                  <button
                    key={ag.id}
                    onClick={() => setSelectedGroup(ag)}
                    className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${
                      selectedGroup?.id === ag.id
                        ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {ag.name}
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right column: agents & keys */}
        <div className="space-y-5">
          {selectedGroup ? (
            <>
              <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
                <h2 className="text-base font-semibold text-gray-800 mb-3">
                  Agents <span className="text-gray-400 font-normal text-xs">in {selectedGroup.name}</span>
                </h2>
                <div className="flex gap-2 mb-4">
                  <input
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && createAgent()}
                    placeholder="New agent name"
                    className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={createAgent}
                    className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
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
                      className="border border-gray-100 rounded-lg p-4 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm text-gray-800">{agent.name}</span>
                        {statusBadge(agent.status)}
                      </div>
                      <p className="text-xs text-gray-400 font-mono">{agent.id}</p>

                      {/* Issue key */}
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
              </section>

              {/* Gateway test */}
              {newKey?.plaintext_key && (
                <GatewayTest apiKey={newKey.plaintext_key} />
              )}
            </>
          ) : (
            <div className="bg-gray-50 border border-dashed border-gray-200 rounded-xl p-8 text-center">
              <p className="text-gray-400 text-sm">
                Select or create an agent group to manage agents
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GatewayTest({ apiKey }: { apiKey: string }) {
  const [model, setModel] = useState("mock-model");
  const [message, setMessage] = useState("Hello! Tell me something interesting.");
  const [response, setResponse] = useState<string | null>(null);
  const [stats, setStats] = useState<{ credits: number; latency: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendRequest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await fetch("/api/gateway/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: message }],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Gateway error");
      setResponse(data.choices[0]?.message?.content ?? "");
      setStats({
        credits: data.x_platform?.credits_charged ?? 0,
        latency: data.x_platform?.latency_ms ?? 0,
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Gateway Test</h2>
      <div className="space-y-3">
        <input
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="Model (e.g. gpt-4o, claude-3-5-sonnet-20241022, mock-model)"
          className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
        />
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="Your message"
          className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
        />
        <button
          onClick={sendRequest}
          disabled={loading}
          className="w-full py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Sending…" : "Send via Gateway"}
        </button>
        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}
        {response !== null && (
          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-800 whitespace-pre-wrap">
            {response}
          </div>
        )}
        {stats && (
          <div className="flex gap-4 text-xs text-gray-500">
            <span>Credits charged: <strong className="text-gray-700">{stats.credits}</strong></span>
            <span>Latency: <strong className="text-gray-700">{stats.latency}ms</strong></span>
          </div>
        )}
      </div>
    </section>
  );
}
