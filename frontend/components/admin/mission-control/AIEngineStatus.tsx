"use client";

import type { CapabilityCategory, ProductionHealth } from "../../../types/missionControl";
import { IconServer } from "./icons";
import { IconWrap, SectionCard, SectionTitle, StatusBadge } from "./primitives";

const AI_PIPELINE_CATEGORY = "AI / Pipeline";

function HealthChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-[#1e2030] bg-[#0d0e14] px-3 py-2">
      <span className="text-xs text-gray-400">{label}</span>
      <StatusBadge tone={ok ? "green" : "red"} label={ok ? "ONLINE" : "DEGRADED"} />
    </div>
  );
}

export function AIEngineStatus({
  health,
  capabilityRegistry,
}: {
  health: ProductionHealth;
  capabilityRegistry: CapabilityCategory[];
}) {
  const aiPipeline = capabilityRegistry.find((c) => c.category === AI_PIPELINE_CATEGORY);

  return (
    <div>
      <SectionTitle>AI Engine</SectionTitle>
      <SectionCard padding="p-4 sm:p-5">
        <div className="flex items-center gap-3 mb-4">
          <IconWrap tone="cyan">
            <IconServer className="w-5 h-5" />
          </IconWrap>
          <div>
            <p className="text-sm font-semibold text-gray-200">Pipeline Status</p>
            <p className="text-xs text-gray-600">Health checks vs. registered capabilities</p>
          </div>
        </div>

        <p className="text-[11px] text-gray-600 uppercase tracking-widest mb-2">Health Checked</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-5">
          <HealthChip label="Overall" ok={health.status === "ok"} />
          <HealthChip label="Database" ok={health.database === "ok"} />
          <HealthChip label="FFmpeg" ok={health.ffmpeg === "ok"} />
        </div>

        <p className="text-[11px] text-gray-600 uppercase tracking-widest mb-2">
          Capability Registered — Available in Pipeline
        </p>
        {aiPipeline ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {aiPipeline.capabilities.map((cap) => (
              <div
                key={cap.name}
                className="flex items-center justify-between gap-3 rounded-lg border border-[#1e2030] bg-[#0d0e14] px-3 py-2"
              >
                <span className="text-xs text-gray-400 truncate" title={cap.name}>
                  {cap.name}
                </span>
                <StatusBadge tone="cyan" label="REGISTERED" />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-600">No AI / Pipeline capabilities registered.</p>
        )}
      </SectionCard>
    </div>
  );
}
