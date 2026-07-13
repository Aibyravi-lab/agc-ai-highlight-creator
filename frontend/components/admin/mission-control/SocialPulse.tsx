"use client";

import type { SocialIntegration } from "../../../types/missionControl";
import { IconGlobe } from "./icons";
import { IconWrap, SectionCard, SectionTitle, StatusBadge } from "./primitives";

export function SocialPulse({ integrations }: { integrations: SocialIntegration[] }) {
  const connected = integrations.filter((i) => i.status === "connected").length;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <SectionTitle>Social Pulse</SectionTitle>
        <span className="text-xs text-gray-500 tabular-nums">
          {connected} / {integrations.length} data sources connected
        </span>
      </div>
      <SectionCard padding="p-4 sm:p-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {integrations.map((integration) => (
            <div
              key={integration.platform}
              className="rounded-lg border border-[#1e2030] bg-[#0d0e14] p-3 flex flex-col items-center text-center gap-2"
            >
              <IconWrap tone="neutral">
                <IconGlobe className="w-4 h-4" />
              </IconWrap>
              <p className="text-sm text-gray-300">{integration.platform}</p>
              <StatusBadge
                tone="neutral"
                label={integration.status === "connected" ? "CONNECTED" : "INTEGRATION PENDING"}
              />
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-4">
          Live social intelligence isn&apos;t connected yet — this will populate automatically once a platform is linked.
        </p>
      </SectionCard>
    </div>
  );
}
