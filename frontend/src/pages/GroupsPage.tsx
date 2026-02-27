import { useState } from "react";
import { creditsApi, groupsApi } from "../api";
import { useAuth } from "../context/AuthContext";
import type { Group } from "../types";

export default function GroupsPage() {
  const { groups, selectedGroup, selectGroup, refreshGroups } = useAuth();

  // Create group
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Invite user
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"ADMIN" | "MEMBER">("MEMBER");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  // Purchase credits
  const [creditAmount, setCreditAmount] = useState("100");
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseMsg, setPurchaseMsg] = useState("");

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    setCreating(true);
    try {
      const g = await groupsApi.create(newName.trim());
      setNewName("");
      await refreshGroups();
      selectGroup(g);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create group");
    } finally {
      setCreating(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroup) return;
    setInviteMsg("");
    setInviting(true);
    try {
      await groupsApi.invite(selectedGroup.id, inviteEmail, inviteRole);
      setInviteMsg(`✓ Invited ${inviteEmail} as ${inviteRole}`);
      setInviteEmail("");
    } catch (err) {
      setInviteMsg(
        `✗ ${err instanceof Error ? err.message : "Failed to invite"}`
      );
    } finally {
      setInviting(false);
    }
  };

  const handlePurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroup) return;
    setPurchaseMsg("");
    setPurchasing(true);
    try {
      const entry = await creditsApi.purchase(
        selectedGroup.id,
        parseInt(creditAmount, 10)
      );
      setPurchaseMsg(`✓ Added ${entry.amount.toLocaleString()} credits`);
      setCreditAmount("100");
    } catch (err) {
      setPurchaseMsg(
        `✗ ${err instanceof Error ? err.message : "Purchase failed"}`
      );
    } finally {
      setPurchasing(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Groups & Credits</h2>
        <p className="text-gray-400 text-sm mt-0.5">
          Manage workspaces, members, and credits
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Create workspace */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Create New Workspace
          </h3>
          {createError && (
            <p className="mb-3 text-sm text-red-600">{createError}</p>
          )}
          <form onSubmit={handleCreateGroup} className="flex gap-3">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
              placeholder="Workspace name"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </form>
        </div>

        {/* All groups */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Your Workspaces
          </h3>
          {groups.length === 0 ? (
            <p className="text-sm text-gray-400">No workspaces yet.</p>
          ) : (
            <div className="space-y-2">
              {groups.map((g) => (
                <div
                  key={g.id}
                  onClick={() => selectGroup(g)}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedGroup?.id === g.id
                      ? "bg-blue-50 border border-blue-200"
                      : "bg-gray-50 hover:bg-gray-100"
                  }`}
                >
                  <div>
                    <p className="text-sm font-medium text-gray-800">{g.name}</p>
                    <p className="text-xs text-gray-400 font-mono">
                      {g.id.slice(0, 8)}…
                    </p>
                  </div>
                  {selectedGroup?.id === g.id && (
                    <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
                      active
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Purchase credits */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-1">
            Purchase Credits
          </h3>
          <p className="text-xs text-gray-400 mb-4">
            Active workspace:{" "}
            <span className="font-medium text-gray-600">
              {selectedGroup?.name ?? "none selected"}
            </span>
          </p>
          {purchaseMsg && (
            <p
              className={`mb-3 text-sm ${
                purchaseMsg.startsWith("✓")
                  ? "text-green-600"
                  : "text-red-600"
              }`}
            >
              {purchaseMsg}
            </p>
          )}
          <form onSubmit={handlePurchase} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Amount (credits)
              </label>
              <div className="flex gap-2 mb-2">
                {[100, 500, 1000, 5000].map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    onClick={() => setCreditAmount(String(amt))}
                    className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
                      creditAmount === String(amt)
                        ? "bg-blue-600 text-white border-blue-600"
                        : "text-gray-600 border-gray-300 hover:border-blue-400"
                    }`}
                  >
                    {amt.toLocaleString()}
                  </button>
                ))}
              </div>
              <input
                type="number"
                min={1}
                value={creditAmount}
                onChange={(e) => setCreditAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={purchasing || !selectedGroup}
              className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {purchasing
                ? "Processing…"
                : `Add ${parseInt(creditAmount || "0").toLocaleString()} Credits`}
            </button>
          </form>
        </div>

        {/* Invite user */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-1">
            Invite Member
          </h3>
          <p className="text-xs text-gray-400 mb-4">
            Invite to:{" "}
            <span className="font-medium text-gray-600">
              {selectedGroup?.name ?? "none selected"}
            </span>
          </p>
          {inviteMsg && (
            <p
              className={`mb-3 text-sm ${
                inviteMsg.startsWith("✓") ? "text-green-600" : "text-red-600"
              }`}
            >
              {inviteMsg}
            </p>
          )}
          <form onSubmit={handleInvite} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Email
              </label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
                placeholder="colleague@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Role
              </label>
              <select
                value={inviteRole}
                onChange={(e) =>
                  setInviteRole(e.target.value as "ADMIN" | "MEMBER")
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="MEMBER">Member</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={inviting || !selectedGroup}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {inviting ? "Inviting…" : "Send Invite"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
