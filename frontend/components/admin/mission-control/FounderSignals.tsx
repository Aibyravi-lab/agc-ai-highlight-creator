"use client";

import type { ReactNode } from "react";
import type { Distribution, LiveMetrics } from "../../../types/missionControl";
import { IconAlertTriangle, IconCreditCard, IconRepeat, IconUsers } from "./icons";
import { IconWrap, SectionCard, SectionTitle } from "./primitives";

interface Signal {
  id: string;
  icon: ReactNode;
  tone: "green" | "cyan" | "amber" | "red";
  message: string;
}

function buildSignals(metrics: LiveMetrics, distribution: Distribution): Signal[] {
  const signals: Signal[] = [];

  if (metrics.users_with_jobs > 0) {
    signals.push({
      id: "tried_ai",
      icon: <IconUsers className="w-4 h-4" />,
      tone: "cyan",
      message: `${metrics.users_with_jobs} creator${metrics.users_with_jobs === 1 ? "" : "s"} have tried the AI.`,
    });
  }

  if (metrics.repeat_users > 0) {
    signals.push({
      id: "repeat_users",
      icon: <IconRepeat className="w-4 h-4" />,
      tone: "green",
      message: `${metrics.repeat_users} creator${metrics.repeat_users === 1 ? "" : "s"} returned for another AI run.`,
    });
  }

  if (metrics.processed_payments > 0) {
    signals.push({
      id: "payments",
      icon: <IconCreditCard className="w-4 h-4" />,
      tone: "green",
      message: `${metrics.processed_payments} payment${metrics.processed_payments === 1 ? "" : "s"} processed.`,
    });
  }

  if (distribution.credit_breakdown.exhausted > 0) {
    signals.push({
      id: "exhausted_credits",
      icon: <IconAlertTriangle className="w-4 h-4" />,
      tone: "amber",
      message: `${distribution.credit_breakdown.exhausted} user${distribution.credit_breakdown.exhausted === 1 ? "" : "s"} exhausted their free credits.`,
    });
  }

  if (metrics.failed_jobs > 0) {
    signals.push({
      id: "failed_jobs",
      icon: <IconAlertTriangle className="w-4 h-4" />,
      tone: "red",
      message: `${metrics.failed_jobs} job${metrics.failed_jobs === 1 ? "" : "s"} have failed.`,
    });
  }

  return signals;
}

export function FounderSignals({
  metrics,
  distribution,
}: {
  metrics: LiveMetrics;
  distribution: Distribution;
}) {
  const signals = buildSignals(metrics, distribution);

  return (
    <div>
      <SectionTitle>Founder Signals</SectionTitle>
      <SectionCard padding="p-3 sm:p-4">
        {signals.length === 0 ? (
          <p className="text-sm text-gray-500 px-1 py-1">No product signals yet — check back as usage grows.</p>
        ) : (
          <ul className="space-y-1">
            {signals.map((signal) => (
              <li key={signal.id} className="flex items-center gap-3 px-1 py-1.5">
                <IconWrap tone={signal.tone}>{signal.icon}</IconWrap>
                <span className="text-sm text-gray-300">{signal.message}</span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
