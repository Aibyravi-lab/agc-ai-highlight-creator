"use client";

import type { Distribution } from "../../../types/missionControl";
import { SectionCard, SectionTitle } from "./primitives";

function MiniStat({ label, value, accent = "text-gray-300" }: { label: string; value: number; accent?: string }) {
  return (
    <div className="text-center">
      <p className={`text-lg font-bold tabular-nums ${accent}`}>{value}</p>
      <p className="text-[10px] text-gray-600 uppercase tracking-wide mt-0.5">{label}</p>
    </div>
  );
}

export function DistributionPanel({ distribution }: { distribution: Distribution }) {
  const { credit_breakdown, jobs_per_user } = distribution;

  return (
    <div>
      <SectionTitle>Credit &amp; Usage Distribution</SectionTitle>
      <div className="grid sm:grid-cols-2 gap-3">
        <SectionCard padding="p-3 sm:p-4">
          <p className="text-[11px] text-gray-600 uppercase tracking-widest mb-3">Credit Breakdown</p>
          <div className="grid grid-cols-3 gap-2">
            <MiniStat label="Exhausted" value={credit_breakdown.exhausted} accent="text-red-400" />
            <MiniStat label="Low" value={credit_breakdown.low} accent="text-amber-400" />
            <MiniStat label="Healthy" value={credit_breakdown.healthy} accent="text-green-400" />
          </div>
        </SectionCard>
        <SectionCard padding="p-3 sm:p-4">
          <p className="text-[11px] text-gray-600 uppercase tracking-widest mb-3">Jobs per User</p>
          <div className="grid grid-cols-4 gap-2">
            <MiniStat label="1" value={jobs_per_user["1"]} />
            <MiniStat label="2-3" value={jobs_per_user["2-3"]} />
            <MiniStat label="4-5" value={jobs_per_user["4-5"]} />
            <MiniStat label="6+" value={jobs_per_user["6+"]} accent="text-emerald-400" />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
