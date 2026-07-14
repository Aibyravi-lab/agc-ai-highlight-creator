"use client";

import type { ReactNode } from "react";
import type { Distribution, FeedbackSummary, LiveMetrics } from "../../../types/missionControl";
import { IconAlertTriangle, IconCreditCard, IconRepeat, IconUsers } from "./icons";
import { IconWrap, SectionCard, SectionTitle } from "./primitives";

interface Signal {
  id: string;
  icon: ReactNode;
  tone: "green" | "cyan" | "amber" | "red";
  message: string;
}

// GROW-005: raw improvement_area values -> founder-readable labels.
const IMPROVEMENT_AREA_LABELS: Record<string, string> = {
  highlight_selection: "Highlight selection",
  clip_timing: "Clip timing",
  processing_speed: "Processing speed",
  captions: "Captions",
  other: "Other",
};

function buildSignals(
  metrics: LiveMetrics,
  distribution: Distribution,
  feedbackSummary: FeedbackSummary
): Signal[] {
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
      message: `${metrics.repeat_users} creator${metrics.repeat_users === 1 ? "" : "s"} came back on a different day to run the AI again.`,
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

  if (metrics.external_failed_jobs > 0) {
    signals.push({
      id: "failed_jobs",
      icon: <IconAlertTriangle className="w-4 h-4" />,
      tone: "red",
      message: `${metrics.external_failed_jobs} job${metrics.external_failed_jobs === 1 ? "" : "s"} have failed.`,
    });
  }

  // GROW-005: feedback intelligence, only shown once real responses exist.
  if (feedbackSummary.total_responses > 0) {
    signals.push({
      id: "feedback_users",
      icon: <IconUsers className="w-4 h-4" />,
      tone: "cyan",
      message: `${metrics.distinct_feedback_users} user${
        metrics.distinct_feedback_users === 1 ? "" : "s"
      } rated their Vedzovi results.`,
    });

    if (feedbackSummary.positive_rate !== null) {
      signals.push({
        id: "feedback_positive_rate",
        icon: <IconRepeat className="w-4 h-4" />,
        tone: feedbackSummary.positive_rate >= 50 ? "green" : "amber",
        message: `${feedbackSummary.positive_rate}% of feedback is Great or Good.`,
      });
    }

    if (feedbackSummary.top_improvement_area) {
      const label =
        IMPROVEMENT_AREA_LABELS[feedbackSummary.top_improvement_area] ??
        feedbackSummary.top_improvement_area;
      signals.push({
        id: "top_improvement_area",
        icon: <IconAlertTriangle className="w-4 h-4" />,
        tone: "amber",
        message: `${label} is the most reported improvement area.`,
      });
    }
  }

  return signals;
}

export function FounderSignals({
  metrics,
  distribution,
  feedbackSummary,
}: {
  metrics: LiveMetrics;
  distribution: Distribution;
  feedbackSummary: FeedbackSummary;
}) {
  const signals = buildSignals(metrics, distribution, feedbackSummary);

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
