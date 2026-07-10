"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  login as apiLogin,
  register as apiRegister,
  getCurrentUser,
} from "../services/auth";
import type { AuthUser, AuthContextValue } from "../types/auth";

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("agc_token");
    if (!token) {
      setLoading(false);
      return;
    }
    getCurrentUser(token)
      .then(setUser)
      .catch(() => localStorage.removeItem("agc_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { token, user } = await apiLogin(email, password);
    localStorage.setItem("agc_token", token);
    setUser(user);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      // AGC-070: registration does not establish a session — the account
      // is created unverified and must be verified before login. No token
      // is stored and no user state is set here.
      return apiRegister(name, email, password);
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem("agc_token");
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem("agc_token");
    if (!token) return;
    try {
      setUser(await getCurrentUser(token));
    } catch {
      // Ignore transient refresh failures; existing session state is kept.
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
