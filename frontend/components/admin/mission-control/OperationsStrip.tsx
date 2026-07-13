"use client";

import type { ProductionHealth, ReleaseInfo } from "../../../types/missionControl";

function formatUptime(uptimeSeconds: number): string {
  const hours = Math.floor(uptimeSeconds / 3600);
  const minutes = Math.floor((uptimeSeconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

export function OperationsStrip({
  release,
  health,
}: {
  release: ReleaseInfo;
  health: ProductionHealth;
}) {
  return (
    <div className="pt-4 border-t border-[#1a1d2e]">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11px] text-gray-600 font-mono">
        <span>v{release.app_version}</span>
        <span>{release.git_commit}</span>
        <span>{release.git_tag}</span>
        <span>{release.ci.workflow}</span>
        <span>uptime {formatUptime(health.uptime_seconds)}</span>
      </div>
      <p className="text-[11px] text-gray-700 mt-1">{release.ci.note}</p>
    </div>
  );
}
