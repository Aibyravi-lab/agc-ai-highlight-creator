"use client";

import type { ReactNode } from "react";
import type { LiveMetrics } from "../../../types/missionControl";
import { useCountUp } from "../../../hooks/useCountUp";
import { IconActivity, IconCreditCard, IconCrown, IconFilm, IconRepeat, IconUsers } from "./icons";
import { IconWrap } from "./primitives";

function ratio(numerator: number, denominator: number): string | null {
  if (denominator <= 0) return null;
  return `${Math.round((numerator / denominator) * 100)}%`;
}

function HeroCard({
  icon,
  tone,
  label,
  value,
  secondary,
}: {
  icon: ReactNode;
  tone: "green" | "cyan" | "purple";
  label: string;
  value: number;
  secondary?: string | null;
}) {
  const displayValue = useCountUp(value);

  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4 relative overflow-hidden">
      <div
        className={`absolute inset-x-0 top-0 h-0.5 ${
          tone === "green" ? "bg-green-500/60" : tone === "cyan" ? "bg-cyan-500/60" : "bg-purple-500/60"
        }`}
      />
      <div className="flex items-center gap-3">
        <IconWrap tone={tone}>{icon}</IconWrap>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">{label}</p>
      </div>
      <p className="text-3xl font-bold mt-3 tabular-nums">{displayValue.toLocaleString()}</p>
      {secondary && <p className="text-xs text-gray-500 mt-1">{secondary}</p>}
    </div>
  );
}

export function HeroMetrics({ metrics }: { metrics: LiveMetrics }) {
  const verifiedRate = ratio(metrics.verified_users, metrics.total_users);
  const completionRate = ratio(metrics.completed_jobs, metrics.total_jobs);
  const repeatRate = ratio(metrics.repeat_users, metrics.users_with_jobs);
  const proRate = ratio(metrics.active_pro_users, metrics.total_users);

  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <HeroCard
          icon={<IconUsers />}
          tone="green"
          label="Total Users"
          value={metrics.total_users}
          secondary={verifiedRate ? `${metrics.verified_users}/${metrics.total_users} verified · ${verifiedRate}` : null}
        />
        <HeroCard
          icon={<IconActivity />}
          tone="cyan"
          label="AI Runs"
          value={metrics.total_jobs}
          secondary={`${metrics.users_with_jobs} creators tried it`}
        />
        <HeroCard
          icon={<IconFilm />}
          tone="green"
          label="Highlights Completed"
          value={metrics.completed_jobs}
          secondary={completionRate ? `${completionRate} completion rate` : null}
        />
        <HeroCard
          icon={<IconRepeat />}
          tone="cyan"
          label="Repeat Users"
          value={metrics.repeat_users}
          secondary={repeatRate ? `${repeatRate} of active users` : null}
        />
        <HeroCard
          icon={<IconCrown />}
          tone="purple"
          label="Active PRO"
          value={metrics.active_pro_users}
          secondary={proRate ? `${proRate} conversion` : null}
        />
        <HeroCard
          icon={<IconCreditCard />}
          tone="purple"
          label="Processed Payments"
          value={metrics.processed_payments}
          secondary="lifetime"
        />
      </div>
    </div>
  );
}
