"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { clearAuthSession, fetchCurrentUser, getStoredUser, login as apiLogin, logout as apiLogout, type AuthUser, type UserRole } from "@/lib/api";

type AuthContextType = {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: UserRole[]) => boolean;
  canMutate: boolean;
  canAudit: boolean;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
  hasRole: () => false,
  canMutate: false,
  canAudit: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
      fetchCurrentUser()
        .then(setUser)
        .catch(() => {
          clearAuthSession();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const session = await apiLogin(username, password);
    setUser(session.user);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextType>(() => {
    const hasRole = (...roles: UserRole[]) => Boolean(user && roles.includes(user.role));
    return {
      user,
      loading,
      login,
      logout,
      hasRole,
      canMutate: hasRole("ADMIN", "OPERATOR"),
      canAudit: hasRole("ADMIN", "AUDITOR"),
    };
  }, [loading, login, logout, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
