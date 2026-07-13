"use client";

import type {
  Blocker,
  CapabilityCategory,
  Distribution,
  LiveMetrics,
  MissionControlSummary,
  ProductionHealth,
  ReleaseInfo,
} from "../../types/missionControl";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
      {children}
    </h2>
  );
}

function MetricTile({
  label,
  value,
  accentText = "text-green-400",
}: {
  label: string;
  value: number | string;
  accentText?: string;
}) {
  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
        {label}
      </p>
      <p className={`text-3xl font-bold mt-2 ${accentText}`}>{value}</p>
    </div>
  );
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        ok
          ? "bg-green-500/15 text-green-400 border border-green-500/30"
          : "bg-red-500/15 text-red-400 border border-red-500/30"
      }`}
    >
      {label}
    </span>
  );
}

function ProductionHealthPanel({ health }: { health: ProductionHealth }) {
  const hours = Math.floor(health.uptime_seconds / 3600);
  const minutes = Math.floor((health.uptime_seconds % 3600) / 60);

  return (
    <div>
      <SectionTitle>Production Health</SectionTitle>
      <div className="rounded-xl border border-[#1e2030] bg-[#0d0e14] p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">Overall</p>
          <StatusBadge ok={health.status === "ok"} label={health.status} />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Database</p>
          <StatusBadge ok={health.database === "ok"} label={health.database} />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">FFmpeg</p>
          <StatusBadge ok={health.ffmpeg === "ok"} label={health.ffmpeg} />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Maintenance Mode</p>
          <StatusBadge
            ok={!health.maintenance_mode}
            label={health.maintenance_mode ? "ON" : "OFF"}
          />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Uptime</p>
          <p className="text-sm text-gray-300">{hours}h {minutes}m</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Environment</p>
          <p className="text-sm text-gray-300">{health.environment}</p>
        </div>
      </div>
    </div>
  );
}

function LiveMetricsPanel({ metrics }: { metrics: LiveMetrics }) {
  return (
    <div>
      <SectionTitle>Live Product Metrics</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricTile label="Total Users" value={metrics.total_users} />
        <MetricTile label="Verified Users" value={metrics.verified_users} />
        <MetricTile label="Users w/ Jobs" value={metrics.users_with_jobs} />
        <MetricTile label="Completed-Job Users" value={metrics.users_with_completed_jobs} />
        <MetricTile label="Repeat Users (2+)" value={metrics.repeat_users} />
        <MetricTile label="Active PRO Users" value={metrics.active_pro_users} accentText="text-purple-400" />
        <MetricTile label="Total Jobs" value={metrics.total_jobs} />
        <MetricTile label="Completed Jobs" value={metrics.completed_jobs} accentText="text-green-400" />
        <MetricTile label="Failed Jobs" value={metrics.failed_jobs} accentText="text-red-400" />
        <MetricTile label="Processed Payments" value={metrics.processed_payments} accentText="text-emerald-400" />
        <MetricTile label="Feedback Users" value={metrics.distinct_feedback_users} />
      </div>
    </div>
  );
}

function DistributionPanel({ distribution }: { distribution: Distribution }) {
  const { credit_breakdown, jobs_per_user } = distribution;

  return (
    <div>
      <SectionTitle>User / Job Distribution</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4">
          <p className="text-xs text-gray-500 mb-3">Credit Breakdown</p>
          <div className="grid grid-cols-3 gap-3">
            <MetricTile label="Exhausted" value={credit_breakdown.exhausted} accentText="text-red-400" />
            <MetricTile label="Low" value={credit_breakdown.low} accentText="text-yellow-400" />
            <MetricTile label="Healthy" value={credit_breakdown.healthy} accentText="text-green-400" />
          </div>
        </div>
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4">
          <p className="text-xs text-gray-500 mb-3">Jobs per User</p>
          <div className="grid grid-cols-4 gap-3">
            <MetricTile label="1 job" value={jobs_per_user["1"]} />
            <MetricTile label="2-3 jobs" value={jobs_per_user["2-3"]} />
            <MetricTile label="4-5 jobs" value={jobs_per_user["4-5"]} />
            <MetricTile label="6+ jobs" value={jobs_per_user["6+"]} accentText="text-emerald-400" />
          </div>
        </div>
      </div>
    </div>
  );
}

function CapabilityRegistryPanel({ registry }: { registry: CapabilityCategory[] }) {
  return (
    <div>
      <SectionTitle>Capability Registry</SectionTitle>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {registry.map((group) => (
          <div key={group.category} className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-4">
            <p className="text-sm font-semibold text-green-400 mb-3">{group.category}</p>
            <ul className="space-y-2">
              {group.capabilities.map((cap) => (
                <li key={cap.name} className="text-sm">
                  <p className="text-gray-300">{cap.name}</p>
                  <p className="text-xs text-gray-600 font-mono truncate" title={cap.evidence}>
                    {cap.evidence}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function BlockersPanel({ blockers }: { blockers: Blocker[] }) {
  return (
    <div>
      <SectionTitle>Blockers / Signals</SectionTitle>
      {blockers.length === 0 ? (
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
          <p className="text-sm text-green-400">No blockers detected.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {blockers.map((blocker) => (
            <div
              key={blocker.id}
              className={`rounded-xl border p-4 ${
                blocker.severity === "warning"
                  ? "border-yellow-500/25 bg-yellow-500/5"
                  : "border-blue-500/20 bg-blue-500/5"
              }`}
            >
              <p
                className={`text-sm ${
                  blocker.severity === "warning" ? "text-yellow-300" : "text-blue-200"
                }`}
              >
                {blocker.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReleasePanel({ release }: { release: ReleaseInfo }) {
  return (
    <div>
      <SectionTitle>Current Release / Operations</SectionTitle>
      <div className="rounded-xl border border-[#1e2030] bg-[#0d0e14] p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">App Version</p>
          <p className="text-sm text-gray-300 font-mono">{release.app_version}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Git Commit</p>
          <p className="text-sm text-gray-300 font-mono">{release.git_commit}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Git Tag</p>
          <p className="text-sm text-gray-300 font-mono">{release.git_tag}</p>
        </div>
        <div className="col-span-2 md:col-span-1">
          <p className="text-xs text-gray-500 mb-1">CI</p>
          <p className="text-sm text-gray-300">{release.ci.workflow}</p>
        </div>
      </div>
      <p className="text-xs text-gray-600 mt-2">{release.ci.note}</p>
    </div>
  );
}

export function MissionControlDashboard({ summary }: { summary: MissionControlSummary }) {
  return (
    <div className="space-y-8">
      <ProductionHealthPanel health={summary.production_health} />
      <LiveMetricsPanel metrics={summary.live_metrics} />
      <DistributionPanel distribution={summary.distribution} />
      <CapabilityRegistryPanel registry={summary.capability_registry} />
      <BlockersPanel blockers={summary.blockers} />
      <ReleasePanel release={summary.release} />
    </div>
  );
}
