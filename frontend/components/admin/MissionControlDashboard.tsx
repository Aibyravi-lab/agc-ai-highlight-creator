"use client";

import type { MissionControlSummary } from "../../types/missionControl";
import { AIEngineStatus } from "./mission-control/AIEngineStatus";
import { ActivityChart } from "./mission-control/ActivityChart";
import { BlockersPanel } from "./mission-control/BlockersPanel";
import { CapabilityRegistry } from "./mission-control/CapabilityRegistry";
import { CommandHeader } from "./mission-control/CommandHeader";
import { DistributionPanel } from "./mission-control/DistributionPanel";
import { FounderSignals } from "./mission-control/FounderSignals";
import { HeroMetrics } from "./mission-control/HeroMetrics";
import { OperationsStrip } from "./mission-control/OperationsStrip";
import { SegmentationBanner } from "./mission-control/SegmentationBanner";
import { SocialPulse } from "./mission-control/SocialPulse";
import { UserFunnel } from "./mission-control/UserFunnel";

export function MissionControlDashboard({
  summary,
  lastUpdatedAt,
}: {
  summary: MissionControlSummary;
  lastUpdatedAt: number | null;
}) {
  return (
    <div className="space-y-8">
      <CommandHeader health={summary.production_health} lastUpdatedAt={lastUpdatedAt} />
      <SegmentationBanner segmentation={summary.segmentation} />
      <HeroMetrics metrics={summary.live_metrics} />
      <ActivityChart activity={summary.weekly_activity} />
      <UserFunnel metrics={summary.live_metrics} />
      <DistributionPanel distribution={summary.distribution} />
      <AIEngineStatus health={summary.production_health} capabilityRegistry={summary.capability_registry} />
      <FounderSignals
        metrics={summary.live_metrics}
        distribution={summary.distribution}
        feedbackSummary={summary.feedback_summary}
      />
      <BlockersPanel blockers={summary.blockers} />
      <CapabilityRegistry registry={summary.capability_registry} />
      <SocialPulse integrations={summary.social_integrations} />
      <OperationsStrip release={summary.release} health={summary.production_health} />
    </div>
  );
}
