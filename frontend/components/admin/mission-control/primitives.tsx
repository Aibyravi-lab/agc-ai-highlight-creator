"use client";

import type { ReactNode } from "react";

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
      {children}
    </h2>
  );
}

export function SectionCard({
  children,
  className = "",
  padding = "p-4",
}: {
  children: ReactNode;
  className?: string;
  padding?: string;
}) {
  return (
    <div className={`rounded-xl border border-[#1e2030] bg-[#0f1117] ${padding} ${className}`}>
      {children}
    </div>
  );
}

type BadgeTone = "green" | "red" | "amber" | "cyan" | "purple" | "neutral";

const BADGE_TONE_CLASSES: Record<BadgeTone, string> = {
  green: "bg-green-500/15 text-green-400 border border-green-500/30",
  red: "bg-red-500/15 text-red-400 border border-red-500/30",
  amber: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  cyan: "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30",
  purple: "bg-purple-500/15 text-purple-400 border border-purple-500/30",
  neutral: "bg-gray-500/15 text-gray-400 border border-gray-500/30",
};

export function StatusBadge({ tone, label }: { tone: BadgeTone; label: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${BADGE_TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}

export function IconWrap({
  children,
  tone = "green",
}: {
  children: ReactNode;
  tone?: BadgeTone;
}) {
  const toneClass: Record<BadgeTone, string> = {
    green: "bg-green-500/10 text-green-400",
    red: "bg-red-500/10 text-red-400",
    amber: "bg-amber-500/10 text-amber-400",
    cyan: "bg-cyan-500/10 text-cyan-400",
    purple: "bg-purple-500/10 text-purple-400",
    neutral: "bg-gray-500/10 text-gray-400",
  };

  return (
    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${toneClass[tone]}`}>
      {children}
    </div>
  );
}
