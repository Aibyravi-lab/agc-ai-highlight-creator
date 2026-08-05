"use client";

import { useState } from "react";
import { useHealthHistory } from "../../../hooks/useHealthHistory";
import type { HealthHistoryRange, HealthSnapshot, TrendDirection } from "../../../types/health";
import { SectionCard, SectionTitle } from "../mission-control/primitives";

const RANGE_OPTIONS: { key: HealthHistoryRange; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "7d", label: "7 Days" },
  { key: "30d", label: "30 Days" },
];

const DIRECTION_COPY: Record<TrendDirection, string> = {
  improving: "↑ Improving",
  declining: "↓ Declining",
  stable: "→ Stable",
  unknown: "— No data",
};

const DIRECTION_COLOR: Record<TrendDirection, string> = {
  improving: "text-green-400",
  declining: "text-red-400",
  stable: "text-gray-400",
  unknown: "text-gray-600",
};

function scoreColor(score: number): string {
  if (score >= 90) return "bg-green-500/70";
  if (score >= 70) return "bg-amber-500/70";
  return "bg-red-500/70";
}

function Sparkline({ snapshots }: { snapshots: HealthSnapshot[] }) {
  if (snapshots.length === 0) {
    return <p className="text-xs text-gray-600 py-8 text-center">No snapshots recorded for this range yet.</p>;
  }

  return (
    <div className="flex items-end gap-1 h-24">
      {snapshots.map((snapshot, index) => (
        <div
          key={`${snapshot.created_at}-${index}`}
          className={`flex-1 min-w-[2px] rounded-t-sm ${scoreColor(snapshot.score)}`}
          style={{ height: `${Math.max(4, snapshot.score)}%` }}
          title={`${snapshot.score} at ${snapshot.created_at}`}
        />
      ))}
    </div>
  );
}

function TrendStat({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div>
      <p className="text-[10px] text-gray-600 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-semibold tabular-nums mt-0.5">{value ?? "—"}</p>
    </div>
  );
}

export function HistoryPanel() {
  const [range, setRange] = useState<HealthHistoryRange>("today");
  const { history, loading, error } = useHealthHistory(range);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <SectionTitle>History &amp; Trend</SectionTitle>
        <div className="flex items-center gap-1 rounded-lg border border-[#1e2030] p-0.5">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setRange(option.key)}
              className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
                range === option.key ? "bg-green-500/15 text-green-400" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <SectionCard padding="p-4 sm:p-5">
        {error && <p className="text-xs text-red-300 mb-3">{error}</p>}

        {loading && !history ? (
          <p className="text-xs text-gray-600 py-8 text-center">Loading history…</p>
        ) : history ? (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
              <TrendStat label="Current" value={history.trend.current_score} />
              <TrendStat label="Average" value={history.trend.avg_score} />
              <TrendStat label="Min" value={history.trend.min_score} />
              <TrendStat label="Max" value={history.trend.max_score} />
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider">Direction</p>
                <p className={`text-sm font-semibold mt-0.5 ${DIRECTION_COLOR[history.trend.direction]}`}>
                  {DIRECTION_COPY[history.trend.direction]}
                </p>
              </div>
            </div>
            <Sparkline snapshots={history.snapshots} />
          </>
        ) : null}
      </SectionCard>
    </div>
  );
}
