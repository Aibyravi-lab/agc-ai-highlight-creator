"use client";

import type { DailyActivity } from "../../../types/missionControl";
import { SectionCard, SectionTitle } from "./primitives";

function dayOfWeek(dateStr: string): string {
  return new Date(`${dateStr}T00:00:00Z`).toLocaleDateString("en-US", {
    weekday: "short",
    timeZone: "UTC",
  });
}

function monthDay(dateStr: string): string {
  return new Date(`${dateStr}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function Bar({ day, maxTotal }: { day: DailyActivity; maxTotal: number }) {
  const other = Math.max(0, day.total - day.completed - day.failed);
  const completedPct = (day.completed / maxTotal) * 100;
  const failedPct = (day.failed / maxTotal) * 100;
  const otherPct = (other / maxTotal) * 100;

  return (
    <div className="flex flex-col items-center gap-2 flex-1 min-w-0">
      <div className="w-full h-32 sm:h-40 flex flex-col-reverse rounded-md overflow-hidden bg-[#13151e]">
        {day.total > 0 ? (
          <>
            <div className="w-full bg-green-500/70" style={{ height: `${completedPct}%` }} title={`${day.completed} completed`} />
            <div className="w-full bg-red-500/70" style={{ height: `${failedPct}%` }} title={`${day.failed} failed`} />
            <div className="w-full bg-gray-500/40" style={{ height: `${otherPct}%` }} title={`${other} in progress / queued`} />
          </>
        ) : null}
      </div>
      <p className="text-[10px] text-gray-600 tabular-nums">{day.total}</p>
      <p className="text-[10px] text-gray-500">
        <span className="sm:hidden">{dayOfWeek(day.date)}</span>
        <span className="hidden sm:inline">{monthDay(day.date)}</span>
      </p>
    </div>
  );
}

export function ActivityChart({ activity }: { activity: DailyActivity[] }) {
  const maxTotal = Math.max(1, ...activity.map((d) => d.total));

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <SectionTitle>AI Activity — Last 7 Days</SectionTitle>
        <div className="flex items-center gap-3 text-[10px] text-gray-500 mb-3">
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500/70" /> Completed
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500/70" /> Failed
          </span>
        </div>
      </div>
      <SectionCard padding="p-4 sm:p-5">
        <div className="flex items-end gap-2 sm:gap-3">
          {activity.map((day) => (
            <Bar key={day.date} day={day} maxTotal={maxTotal} />
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
