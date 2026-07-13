"use client";

import { Fragment } from "react";
import type { LiveMetrics } from "../../../types/missionControl";
import { IconArrowDown, IconArrowRight } from "./icons";
import { SectionCard, SectionTitle } from "./primitives";

interface Stage {
  label: string;
  value: number;
}

function buildStages(metrics: LiveMetrics): Stage[] {
  return [
    { label: "Signed Up", value: metrics.total_users },
    { label: "Verified", value: metrics.verified_users },
    { label: "Tried AI", value: metrics.users_with_jobs },
    { label: "Returned", value: metrics.repeat_users },
    { label: "Active PRO", value: metrics.active_pro_users },
  ];
}

function conversionFrom(previous: number, current: number): string | null {
  if (previous <= 0) return null;
  return `${Math.round((current / previous) * 100)}%`;
}

function StageCard({ stage }: { stage: Stage }) {
  return (
    <div className="rounded-lg border border-[#1e2030] bg-[#0d0e14] px-4 py-3 text-center min-w-[7rem] w-full sm:w-auto">
      <p className="text-2xl font-bold text-green-400 tabular-nums">{stage.value}</p>
      <p className="text-[11px] text-gray-500 uppercase tracking-widest mt-0.5">{stage.label}</p>
    </div>
  );
}

function Connector({ conversion }: { conversion: string | null }) {
  return (
    <div className="flex sm:flex-col items-center justify-center gap-1 text-gray-600 py-1 sm:py-0 sm:px-1">
      <IconArrowDown className="w-3.5 h-3.5 sm:hidden" />
      <IconArrowRight className="hidden sm:block w-3.5 h-3.5" />
      {conversion && <span className="text-[11px] tabular-nums">{conversion}</span>}
    </div>
  );
}

export function UserFunnel({ metrics }: { metrics: LiveMetrics }) {
  const stages = buildStages(metrics);

  return (
    <div>
      <SectionTitle>User Funnel</SectionTitle>
      <SectionCard padding="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center">
          {stages.map((stage, index) => (
            <Fragment key={stage.label}>
              {index > 0 && (
                <Connector conversion={conversionFrom(stages[index - 1].value, stage.value)} />
              )}
              <StageCard stage={stage} />
            </Fragment>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
