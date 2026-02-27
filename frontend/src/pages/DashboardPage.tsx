import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { groupsApi, usageApi } from "../api";
import { useAuth } from "../context/AuthContext";
import type { BurnRate, TopUser, UsageEvent } from "../types";

function StatCard({
  title,
  value,
  sub,
  accent,
}: {
  title: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${accent ?? "text-gray-900"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { selectedGroup } = useAuth();
  const navigate = useNavigate();
  const [balance, setBalance] = useState<number | null>(null);
  const [burnRate, setBurnRate] = useState<BurnRate | null>(null);
  const [topUsers, setTopUsers] = useState<TopUser[]>([]);
  const [recentUsage, setRecentUsage] = useState<UsageEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (groupId: string) => {
    setLoading(true);
    try {
      const [bal, burn, top, usage] = await Promise.all([
        groupsApi.balance(groupId),
        usageApi.burnRate(groupId),
        usageApi.topUsers(groupId),
        usageApi.history(groupId, 5),
      ]);
      setBalance(bal.balance);
      setBurnRate(burn);
      setTopUsers(top);
      setRecentUsage(usage);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedGroup) {
      load(selectedGroup.id);
    } else {
      setLoading(false);
    }
  }, [selectedGroup, load]);

  if (!selectedGroup) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="text-5xl mb-4">◈</div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">
          No workspace selected
        </h2>
        <p className="text-gray-400 mb-6">
          Create a workspace to get started
        </p>
        <button
          onClick={() => navigate("/groups")}
          className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Create Workspace
        </button>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{selectedGroup.name}</h2>
        <p className="text-gray-400 text-sm mt-0.5">Dashboard overview</p>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Loading…</div>
      ) : (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <StatCard
              title="Credit Balance"
              value={balance?.toLocaleString() ?? "—"}
              sub="credits available"
              accent={
                (balance ?? 0) > 100
                  ? "text-green-600"
                  : (balance ?? 0) > 0
                  ? "text-yellow-600"
                  : "text-red-600"
              }
            />
            <StatCard
              title="Burn Rate (24h)"
              value={burnRate?.credits_last_24h.toLocaleString() ?? "—"}
              sub="credits spent today"
            />
            <StatCard
              title="Burn Rate (7d)"
              value={burnRate?.credits_last_7d.toLocaleString() ?? "—"}
              sub="credits spent this week"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Users */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">
                Top Users by Spend
              </h3>
              {topUsers.length === 0 ? (
                <p className="text-sm text-gray-400">No usage yet.</p>
              ) : (
                <div className="space-y-2">
                  {topUsers.map((u, i) => (
                    <div
                      key={u.user_id}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-gray-400 font-mono w-4">
                          {i + 1}.
                        </span>
                        <span className="text-gray-600 font-mono truncate text-xs">
                          {u.user_id.slice(0, 8)}…
                        </span>
                      </div>
                      <span className="font-medium text-gray-900 shrink-0">
                        {u.total_credits.toLocaleString()} cr
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">
                Recent Activity
              </h3>
              {recentUsage.length === 0 ? (
                <p className="text-sm text-gray-400">No requests yet.</p>
              ) : (
                <div className="space-y-3">
                  {recentUsage.map((ev) => (
                    <div
                      key={ev.id}
                      className="flex items-start justify-between text-sm border-b border-gray-50 pb-2 last:border-0"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-gray-800 truncate">
                          {ev.provider}/{ev.model}
                        </p>
                        <p className="text-xs text-gray-400">
                          {ev.total_tokens.toLocaleString()} tokens ·{" "}
                          {new Date(ev.created_at).toLocaleString()}
                        </p>
                      </div>
                      <span className="ml-4 shrink-0 text-red-500 font-medium">
                        -{ev.credits_charged} cr
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
