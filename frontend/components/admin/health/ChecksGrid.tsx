"use client";

import type { ReactNode } from "react";
import type { CheckStatusValue, HealthCheckEntry } from "../../../types/health";
import { IconAlertTriangle, IconCheckCircle, IconInfo } from "../mission-control/icons";
import { IconWrap, SectionCard, SectionTitle } from "../mission-control/primitives";

const CHECK_LABELS: Record<string, string> = {
  backend: "Backend API",
  frontend: "Frontend",
  database: "Database",
  sqlite_integrity: "SQLite Integrity",
  disk: "Disk Usage",
  memory: "Memory",
  cpu: "CPU Load",
  queue: "Job Queue",
  ai_pipeline: "AI Pipeline",
  payments: "Payments",
  email: "Email Delivery",
  backups: "Backups",
  growth_intelligence: "Growth Intelligence",
};

// Sprint-specified display order (MONITOR section), rather than whatever
// order the backend's dict happens to serialize in.
const CHECK_ORDER = [
  "backend",
  "frontend",
  "database",
  "sqlite_integrity",
  "disk",
  "memory",
  "cpu",
  "queue",
  "ai_pipeline",
  "payments",
  "email",
  "backups",
  "growth_intelligence",
];

const STATUS_STYLES: Record<CheckStatusValue, { tone: "green" | "amber" | "red" | "neutral"; icon: (className?: string) => ReactNode }> = {
  healthy: { tone: "green", icon: (c) => <IconCheckCircle className={c} /> },
  warning: { tone: "amber", icon: (c) => <IconAlertTriangle className={c} /> },
  critical: { tone: "red", icon: (c) => <IconAlertTriangle className={c} /> },
  unknown: { tone: "neutral", icon: (c) => <IconInfo className={c} /> },
};

function CheckCard({ checkId, entry }: { checkId: string; entry: HealthCheckEntry }) {
  const style = STATUS_STYLES[entry.status] ?? STATUS_STYLES.unknown;

  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <IconWrap tone={style.tone}>{style.icon("w-4 h-4")}</IconWrap>
          <p className="text-sm font-medium">{CHECK_LABELS[checkId] ?? checkId}</p>
        </div>
        <span
          className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${
            style.tone === "green"
              ? "text-green-400"
              : style.tone === "amber"
                ? "text-amber-400"
                : style.tone === "red"
                  ? "text-red-400"
                  : "text-gray-500"
          }`}
        >
          {entry.status}
        </span>
      </div>
      <p className="text-xs text-gray-500 mt-2 leading-relaxed">{entry.message}</p>
    </div>
  );
}

export function ChecksGrid({ checks }: { checks: Record<string, HealthCheckEntry> }) {
  const orderedIds = [...CHECK_ORDER, ...Object.keys(checks).filter((id) => !CHECK_ORDER.includes(id))];

  return (
    <div>
      <SectionTitle>System Checks</SectionTitle>
      <SectionCard padding="p-4 sm:p-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {orderedIds
            .filter((id) => checks[id])
            .map((id) => (
              <CheckCard key={id} checkId={id} entry={checks[id]} />
            ))}
        </div>
      </SectionCard>
    </div>
  );
}
