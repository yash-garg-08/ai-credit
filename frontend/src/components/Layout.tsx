import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "/usage", label: "Usage", icon: "⚡" },
  { to: "/pricing", label: "Pricing", icon: "¤" },
  { to: "/groups", label: "Groups & Credits", icon: "◈" },
  { to: "/agents", label: "Agent Governance", icon: "⬡" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { email, groups, selectedGroup, selectGroup, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 bg-gray-900 text-white flex flex-col shrink-0">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-gray-700">
          <h1 className="text-lg font-bold text-white tracking-tight">
            ⚡ AI Credits
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">Platform</p>
        </div>

        {/* Group switcher */}
        <div className="px-4 py-3 border-b border-gray-700">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1.5 px-1">
            Workspace
          </p>
          <select
            className="w-full bg-gray-800 text-white text-sm rounded-md px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500"
            value={selectedGroup?.id ?? ""}
            onChange={(e) => {
              const g = groups.find((g) => g.id === e.target.value);
              if (g) selectGroup(g);
            }}
          >
            {groups.length === 0 && (
              <option value="">No workspaces yet</option>
            )}
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                }`
              }
            >
              <span className="text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-4 py-4 border-t border-gray-700">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">{email}</p>
              <p className="text-xs text-gray-400">Signed in</p>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs text-gray-400 hover:text-white ml-2 shrink-0 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
