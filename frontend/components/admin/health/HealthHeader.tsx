"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { HealthSummary } from "../../../types/health";
import { StatusBadge } from "../mission-control/primitives";

function useSecondsAgo(lastUpdatedAt: number | null): number | null {
  const [secondsAgo, setSecondsAgo] = useState<number | null>(null);

  useEffect(() => {
    if (lastUpdatedAt === null) return;

    const intervalId = setInterval(() => {
      setSecondsAgo(Math.max(0, Math.round((Date.now() - lastUpdatedAt) / 1000)));
    }, 1000);

    return () => clearInterval(intervalId);
  }, [lastUpdatedAt]);

  return secondsAgo;
}

const STATUS_BADGE: Record<HealthSummary["status"], { tone: "green" | "amber" | "red"; label: string }> = {
  healthy: { tone: "green", label: "PRODUCTION HEALTHY" },
  degraded: { tone: "amber", label: "PRODUCTION DEGRADED" },
  critical: { tone: "red", label: "PRODUCTION CRITICAL" },
};

export function HealthHeader({
  summary,
  lastUpdatedAt,
}: {
  summary: HealthSummary;
  lastUpdatedAt: number | null;
}) {
  const secondsAgo = useSecondsAgo(lastUpdatedAt);
  const badge = STATUS_BADGE[summary.status];

  return (
    <div className="pb-4 border-b border-[#1a1d2e]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-green-400 tracking-[0.2em] uppercase">Vedzovi</p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mt-0.5">Production Health</h1>
          <Link
            href="/admin/mission-control"
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors mt-1 inline-block"
          >
            ← Back to Mission Control
          </Link>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-1 text-xs font-medium text-green-400">
            <span className="relative flex w-2 h-2">
              <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full w-2 h-2 bg-green-400" />
            </span>
            LIVE
          </span>
          <StatusBadge tone={badge.tone} label={badge.label} />
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-3">
        {secondsAgo === null ? "Syncing…" : `Updated ${secondsAgo}s ago`}
      </p>
    </div>
  );
}
