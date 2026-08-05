"use client";

import type { OpenAlert } from "../../../types/health";
import { IconAlertTriangle, IconCheckCircle } from "../mission-control/icons";
import { SectionTitle } from "../mission-control/primitives";

function formatTime(iso: string): string {
  try {
    return new Date(`${iso}Z`).toLocaleString();
  } catch {
    return iso;
  }
}

function AlertCard({ alert }: { alert: OpenAlert }) {
  const critical = alert.severity === "critical";

  return (
    <div
      className={`rounded-xl border p-4 flex items-start gap-2.5 ${
        critical ? "border-red-500/30 bg-red-500/5" : "border-amber-500/25 bg-amber-500/5"
      }`}
    >
      <IconAlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${critical ? "text-red-400" : "text-amber-400"}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className={`text-[10px] font-semibold uppercase tracking-widest ${critical ? "text-red-300" : "text-amber-300"} opacity-80`}>
            {alert.severity} · {alert.check_id.replace(/_/g, " ")}
          </p>
          <p className="text-[10px] text-gray-600 shrink-0">{formatTime(alert.time)}</p>
        </div>
        <p className={`text-sm mt-1 ${critical ? "text-red-200" : "text-amber-200"}`}>{alert.root_cause}</p>
        <p className="text-xs text-gray-500 mt-1.5">
          <span className="text-gray-600">Suggested fix:</span> {alert.suggested_fix}
        </p>
      </div>
    </div>
  );
}

export function AlertsPanel({ alerts }: { alerts: OpenAlert[] }) {
  return (
    <div>
      <SectionTitle>Open Alerts</SectionTitle>
      {alerts.length === 0 ? (
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4 flex items-center gap-2">
          <IconCheckCircle className="w-4 h-4 text-green-400" />
          <p className="text-sm text-green-400">No open alerts — every monitored system is within threshold.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
