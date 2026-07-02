"use client";

import { useState, useEffect, useRef } from "react";
import type { PipelineJob } from "../types/pipeline";

interface ProgressPanelProps {
  loading: boolean;
  progress: number;
  progressStatus: string;
  error?: string | null;
  onClearError?: () => void;
  currentJobId: string | null;
  currentJob: PipelineJob | null;
  successMessage?: string | null;
  onClearSuccessMessage?: () => void;
}

function StatusBadge({ label, cls }: { label: string; cls: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {label}
    </span>
  );
}

// Parse the backend's created_at string to a UTC epoch ms value.
//
// Python's datetime.utcnow().isoformat() produces strings like:
//   "2026-06-30T12:05:55.123456"  — no Z, microseconds (6 dp)
//
// JS date-time strings WITHOUT a timezone suffix are treated as LOCAL time
// by the ECMAScript spec, shifting startMs by the user's UTC offset and
// making elapsed appear as a clock value (e.g. "05:30:08").
//
// Fixes applied here:
//  1. Space separator → T  (SQLite stores as "2026-06-30 …")
//  2. Truncate microseconds → milliseconds  (JS only supports 3 dp)
//  3. Append Z when no tz suffix present  (treat as UTC, not local)
function parseCreatedAt(raw: string): number {
  let s = raw.replace(" ", "T");
  s = s.replace(/(\.\d{3})\d+/, "$1");
  if (!/Z$|[+-]\d{2}:?\d{2}$/.test(s)) {
    s += "Z";
  }
  const ms = new Date(s).getTime();
  return isNaN(ms) ? Date.now() : ms;
}

function formatElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  if (h > 0) {
    return `${h.toString().padStart(2, "0")}:${m}:${s}`;
  }
  return `${m}:${s}`;
}

export function ProgressPanel({
  loading,
  progress,
  progressStatus,
  error,
  onClearError,
  currentJobId,
  currentJob,
  successMessage,
  onClearSuccessMessage,
}: ProgressPanelProps) {
  const [elapsed, setElapsed] = useState(0);
  // Pinned once per job — never recalculated on re-render.
  const startMsRef = useRef<number | null>(null);

  useEffect(() => {
    if (!loading || !currentJob?.created_at) {
      startMsRef.current = null;
      setElapsed(0);
      return;
    }

    startMsRef.current = parseCreatedAt(currentJob.created_at);

    const tick = () => {
      const startMs = startMsRef.current;
      if (startMs === null) return;
      const elapsedMs = Date.now() - startMs;
      const totalSec = Math.max(0, Math.floor(elapsedMs / 1000));
      setElapsed(totalSec);
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [loading, currentJob?.created_at]);

  if (!loading && !error && !successMessage) {
    return null;
  }

  const startedTime = currentJob?.created_at
    ? new Date(parseCreatedAt(currentJob.created_at)).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : null;

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-red-400 font-semibold text-sm">Processing Failed</p>
              <p className="mt-1 text-sm text-red-300/70">{error}</p>
            </div>
            {onClearError && (
              <button
                onClick={onClearError}
                className="shrink-0 px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      {successMessage && !loading && !error && (
        <div className="rounded-xl border border-green-500/30 bg-green-950/20 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-green-400 font-semibold text-sm">Processing Complete</p>
              <p className="mt-1 text-sm text-green-300/70">{successMessage}</p>
            </div>
            {onClearSuccessMessage && (
              <button
                onClick={onClearSuccessMessage}
                className="shrink-0 px-4 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-medium"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      {loading && !error && (
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
              Current Job
            </h2>
            <StatusBadge
              label="Running"
              cls="bg-blue-500/15 text-blue-400 border border-blue-500/30"
            />
          </div>

          <div className="flex items-end justify-between mb-3">
            <div aria-live="polite" aria-atomic="true">
              <p className="text-white font-semibold">
                {progressStatus || "Processing…"}
              </p>
            </div>
            <p className="text-3xl font-bold text-blue-400 tabular-nums" aria-hidden="true">
              {progress}%
            </p>
          </div>

          <div
            className="w-full bg-[#1a1d2e] rounded-full h-2 overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Processing: ${progress}% complete`}
          >
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {startedTime && (
            <div className="mt-4 flex items-center gap-5 text-xs text-gray-600">
              <span>Started {startedTime}</span>
              <span className="font-mono" aria-live="off">Elapsed {formatElapsed(elapsed)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
