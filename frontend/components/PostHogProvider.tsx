"use client";

import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { identify } from "../services/analytics";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading || !user) return;
    identify(user.id);
  }, [user, loading]);

  return <>{children}</>;
}
