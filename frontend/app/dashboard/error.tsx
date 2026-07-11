"use client";

import { useEffect } from "react";
import { ErrorFallback } from "../../components/ErrorFallback";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled dashboard error:", error);
  }, [error]);

  return <ErrorFallback reset={reset} />;
}
