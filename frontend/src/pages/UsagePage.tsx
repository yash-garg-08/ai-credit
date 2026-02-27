import { useCallback, useEffect, useRef, useState } from "react";
import { pricingApi, usageApi } from "../api";
import { useAuth } from "../context/AuthContext";
import type { PricingRule, UsageEvent, UsageResponse } from "../types";

export default function UsagePage() {
  const { selectedGroup } = useAuth();

  const [pricing, setPricing] = useState<PricingRule[]>([]);
  const [history, setHistory] = useState<UsageEvent[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Request form
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-model");
  const [message, setMessage] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [result, setResult] = useState<UsageResponse | null>(null);
  const [reqError, setReqError] = useState("");

  const loadHistory = useCallback(async (groupId: string) => {
    setHistoryLoading(true);
    try {
      const events = await usageApi.history(groupId, 20);
      setHistory(events);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    pricingApi.list().then(setPricing).catch(() => {});
    if (selectedGroup) loadHistory(selectedGroup.id);
  }, [selectedGroup, loadHistory]);

  // When provider changes, auto-select first matching model
  const providerModels = pricing.filter((p) => p.provider === provider);
  const uniqueProviders = [...new Set(pricing.map((p) => p.provider))];

  const handleProviderChange = (p: string) => {
    setProvider(p);
    const first = pricing.find((r) => r.provider === p);
    if (first) setModel(first.model);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroup) return;
    setReqError("");
    setResult(null);
    setRequesting(true);
    try {
      const res = await usageApi.request(
        selectedGroup.id,
        provider,
        model,
        message
      );
      setResult(res);
      setMessage("");
      loadHistory(selectedGroup.id);
    } catch (err) {
      setReqError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setRequesting(false);
    }
  };

  if (!selectedGroup) {
    return (
      <div className="p-8 text-gray-400">Select a workspace to make requests.</div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Usage</h2>
        <p className="text-gray-400 text-sm mt-0.5">
          Make AI requests and track consumption
        </p>
      </div>

      {/* Request form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          New Request
        </h3>
        {reqError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {reqError}
          </div>
        )}
        {result && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-green-700 uppercase tracking-wide">
                Response
              </p>
              <span className="text-xs text-green-600 font-mono">
                -{result.credits_charged} credits · {result.input_tokens}↑{" "}
                {result.output_tokens}↓ tokens
              </span>
            </div>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">
              {result.response}
            </p>
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Provider
              </label>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {uniqueProviders.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {providerModels.map((r) => (
                  <option key={r.model} value={r.model}>
                    {r.model}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Message
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Enter your prompt…"
            />
          </div>
          <button
            type="submit"
            disabled={requesting || !message.trim()}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {requesting ? "Sending…" : "Send Request"}
          </button>
        </form>
      </div>

      {/* Usage history */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Usage History
        </h3>
        {historyLoading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : history.length === 0 ? (
          <p className="text-sm text-gray-400">No usage history yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                  <th className="pb-2 font-medium">Provider / Model</th>
                  <th className="pb-2 font-medium">Tokens</th>
                  <th className="pb-2 font-medium">Cost (USD)</th>
                  <th className="pb-2 font-medium text-right">Credits</th>
                  <th className="pb-2 font-medium text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {history.map((ev) => (
                  <tr key={ev.id}>
                    <td className="py-2.5 text-gray-800">
                      <span className="font-medium">{ev.provider}</span>
                      <span className="text-gray-400 mx-1">/</span>
                      <span>{ev.model}</span>
                    </td>
                    <td className="py-2.5 text-gray-500 font-mono text-xs">
                      {ev.total_tokens.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-gray-500 font-mono text-xs">
                      ${parseFloat(ev.cost_usd).toFixed(6)}
                    </td>
                    <td className="py-2.5 text-right font-medium text-red-500">
                      -{ev.credits_charged}
                    </td>
                    <td className="py-2.5 text-right text-gray-400 text-xs">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
