"use client";

import type { HealthSummary } from "../../../types/health";
import { useCountUp } from "../../../hooks/useCountUp";
import { SectionCard } from "../mission-control/primitives";

const STATUS_COLOR: Record<HealthSummary["status"], string> = {
  healthy: "#22c55e",
  degraded: "#f59e0b",
  critical: "#ef4444",
};

const STATUS_COPY: Record<HealthSummary["status"], string> = {
  healthy: "All monitored systems are within normal range.",
  degraded: "One or more systems need attention.",
  critical: "One or more systems require immediate action.",
};

export function ScoreCard({ summary }: { summary: HealthSummary }) {
  const score = useCountUp(summary.score);
  const color = STATUS_COLOR[summary.status];

  return (
    <SectionCard padding="p-5 sm:p-6" className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-0.5" style={{ backgroundColor: `${color}99` }} />
      <div className="flex flex-col sm:flex-row sm:items-center gap-5">
        <div
          className="w-24 h-24 rounded-full flex items-center justify-center shrink-0 border-4"
          style={{ borderColor: `${color}40`, background: `${color}0d` }}
        >
          <span className="text-3xl font-bold tabular-nums" style={{ color }}>
            {score}
          </span>
        </div>
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Production Health Score</p>
          <p className="text-sm text-gray-400 mt-1">{STATUS_COPY[summary.status]}</p>
          <p className="text-[11px] text-gray-600 mt-2">
            {summary.open_alerts.length === 0
              ? "No open alerts."
              : `${summary.open_alerts.length} open alert${summary.open_alerts.length === 1 ? "" : "s"}.`}
          </p>
        </div>
      </div>
    </SectionCard>
  );
}
