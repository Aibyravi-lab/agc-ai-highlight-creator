"use client";

import type { HealthSummary } from "../../types/health";
import { AlertsPanel } from "./health/AlertsPanel";
import { ChecksGrid } from "./health/ChecksGrid";
import { HealthHeader } from "./health/HealthHeader";
import { HistoryPanel } from "./health/HistoryPanel";
import { ScoreCard } from "./health/ScoreCard";

export function HealthDashboard({
  summary,
  lastUpdatedAt,
}: {
  summary: HealthSummary;
  lastUpdatedAt: number | null;
}) {
  return (
    <div className="space-y-8">
      <HealthHeader summary={summary} lastUpdatedAt={lastUpdatedAt} />
      <ScoreCard summary={summary} />
      <AlertsPanel alerts={summary.open_alerts} />
      <ChecksGrid checks={summary.checks} />
      <HistoryPanel />
    </div>
  );
}
