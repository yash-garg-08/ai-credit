import { useEffect, useMemo, useState } from "react";
import { pricingApi } from "../api";
import type { PricingRule } from "../types";

export default function PricingPage() {
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    pricingApi
      .list()
      .then((data) => {
        setRules(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load pricing");
        setLoading(false);
      });
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, PricingRule[]>();
    for (const rule of rules) {
      const existing = map.get(rule.provider) ?? [];
      existing.push(rule);
      map.set(rule.provider, existing);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [rules]);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Pricing</h2>
        <p className="text-gray-400 text-sm mt-0.5">
          Backend pricing rules used for credits calculation
        </p>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading pricing…</p>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && grouped.length === 0 && (
        <p className="text-sm text-gray-500">No pricing rules available.</p>
      )}

      {!loading && !error && grouped.length > 0 && (
        <div className="space-y-5">
          {grouped.map(([provider, providerRules]) => (
            <section key={provider} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
              <h3 className="text-base font-semibold text-gray-800 mb-3 capitalize">{provider}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                      <th className="pb-2 font-medium">Model</th>
                      <th className="pb-2 font-medium">Input / 1K tokens</th>
                      <th className="pb-2 font-medium">Output / 1K tokens</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {providerRules.map((rule) => (
                      <tr key={rule.id}>
                        <td className="py-2.5 text-gray-800">{rule.model}</td>
                        <td className="py-2.5 text-gray-600 font-mono">
                          ${Number(rule.input_cost_per_1k).toFixed(6)}
                        </td>
                        <td className="py-2.5 text-gray-600 font-mono">
                          ${Number(rule.output_cost_per_1k).toFixed(6)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
