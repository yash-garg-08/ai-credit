import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi, groupsApi } from "../api";
import type { Group } from "../types";

interface AuthState {
  token: string | null;
  email: string | null;
  groups: Group[];
  selectedGroup: Group | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  selectGroup: (group: Group) => void;
  refreshGroups: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: localStorage.getItem("token"),
    email: localStorage.getItem("email"),
    groups: [],
    selectedGroup: null,
    loading: true,
  });

  const refreshGroups = useCallback(async () => {
    if (!localStorage.getItem("token")) return;
    try {
      const groups = await groupsApi.myGroups();
      const storedGroupId = localStorage.getItem("selectedGroupId");
      const selected =
        groups.find((g) => g.id === storedGroupId) ?? groups[0] ?? null;
      setState((s) => ({ ...s, groups, selectedGroup: selected, loading: false }));
    } catch {
      setState((s) => ({ ...s, loading: false }));
    }
  }, []);

  useEffect(() => {
    if (state.token) {
      refreshGroups();
    } else {
      setState((s) => ({ ...s, loading: false }));
    }
  }, [state.token, refreshGroups]);

  const login = async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("email", email);
    setState((s) => ({ ...s, token: data.access_token, email, loading: true }));
    const groups = await groupsApi.myGroups();
    const selected = groups[0] ?? null;
    if (selected) localStorage.setItem("selectedGroupId", selected.id);
    setState((s) => ({
      ...s,
      groups,
      selectedGroup: selected,
      loading: false,
    }));
  };

  const register = async (email: string, password: string) => {
    await authApi.register(email, password);
    await login(email, password);
  };

  const logout = () => {
    localStorage.clear();
    setState({
      token: null,
      email: null,
      groups: [],
      selectedGroup: null,
      loading: false,
    });
  };

  const selectGroup = (group: Group) => {
    localStorage.setItem("selectedGroupId", group.id);
    setState((s) => ({ ...s, selectedGroup: group }));
  };

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout, selectGroup, refreshGroups }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
