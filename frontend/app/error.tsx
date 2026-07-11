"use client";

import { useEffect } from "react";
import { ErrorFallback } from "../components/ErrorFallback";

export default function GlobalRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled route error:", error);
  }, [error]);

  return <ErrorFallback reset={reset} />;
}
