"use client";

import type { ReactNode } from "react";
import type { Blocker } from "../../../types/missionControl";
import { IconAlertTriangle, IconCheckCircle, IconInfo } from "./icons";
import { SectionTitle } from "./primitives";

type Tier = "CRITICAL" | "WARNING" | "SIGNAL";

const TIER_STYLES: Record<Tier, { border: string; bg: string; text: string; icon: ReactNode }> = {
  CRITICAL: {
    border: "border-red-500/30",
    bg: "bg-red-500/5",
    text: "text-red-300",
    icon: <IconAlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />,
  },
  WARNING: {
    border: "border-amber-500/25",
    bg: "bg-amber-500/5",
    text: "text-amber-300",
    icon: <IconAlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
  },
  SIGNAL: {
    border: "border-cyan-500/20",
    bg: "bg-cyan-500/5",
    text: "text-cyan-200",
    icon: <IconInfo className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />,
  },
};

function tierFor(blocker: Blocker): Tier {
  if (blocker.id === "maintenance_mode_on") return "CRITICAL";
  if (blocker.severity === "warning") return "WARNING";
  return "SIGNAL";
}

export function BlockersPanel({ blockers }: { blockers: Blocker[] }) {
  return (
    <div>
      <SectionTitle>Blockers / Signals</SectionTitle>
      {blockers.length === 0 ? (
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4 flex items-center gap-2">
          <IconCheckCircle className="w-4 h-4 text-green-400" />
          <p className="text-sm text-green-400">HEALTHY — no blockers detected.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {blockers.map((blocker) => {
            const tier = tierFor(blocker);
            const style = TIER_STYLES[tier];
            return (
              <div key={blocker.id} className={`rounded-xl border ${style.border} ${style.bg} p-4 flex items-start gap-2.5`}>
                {style.icon}
                <div>
                  <p className={`text-[10px] font-semibold uppercase tracking-widest ${style.text} opacity-80`}>
                    {tier}
                  </p>
                  <p className={`text-sm ${style.text}`}>{blocker.message}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
