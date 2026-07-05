"use client";

import { useState, useEffect, useRef } from "react";
import type { PipelineJob } from "../types/pipeline";
import { getFriendlyUploadErrorMessage } from "../utils/uploadErrors";
import { getFriendlyStageMessage } from "../utils/processingStages";

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
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold flex-shrink-0 ${cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
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
        <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center text-red-400 flex-shrink-0">
              <IconAlert />
            </div>
            <div className="flex-1 min-w-0 flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-red-400 font-semibold text-sm">Processing Failed</p>
                <p className="mt-1 text-sm text-red-300/70 whitespace-pre-line">
                  {getFriendlyUploadErrorMessage(error)}
                </p>
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
        </div>
      )}

      {successMessage && !loading && !error && (
        <div className="rounded-2xl border border-green-500/30 bg-green-950/20 p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center text-green-400 flex-shrink-0">
              <IconCheckCircle />
            </div>
            <div className="flex-1 min-w-0 flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-green-400 font-semibold text-sm">Highlights generated successfully!</p>
                <p className="mt-1 text-sm text-green-300/70">
                  Your video is ready to explore — scroll down to view your highlights.
                </p>
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
        </div>
      )}

      {loading && !error && (
        <div className="rounded-2xl border border-[#1a1d2e] bg-[#0d0e14] p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3 mb-6">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0">
                <IconSpinner />
              </div>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest truncate">
                Processing Your Video
              </h2>
            </div>
            <StatusBadge
              label="Running"
              cls="bg-blue-500/15 text-blue-400 border border-blue-500/30"
            />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-4">
            <div aria-live="polite" aria-atomic="true" className="min-w-0">
              <p className="text-white font-semibold text-base truncate">
                {getFriendlyStageMessage(progressStatus)}
              </p>
            </div>
            <p className="text-4xl font-bold text-blue-400 tabular-nums leading-none" aria-hidden="true">
              {progress}%
            </p>
          </div>

          <div
            className="w-full bg-[#1a1d2e] rounded-full h-2.5 overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Processing: ${progress}% complete`}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {startedTime && (
            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-600">
              <span>Started {startedTime}</span>
              <span className="font-mono" aria-live="off">Elapsed {formatElapsed(elapsed)}</span>
            </div>
          )}

          <div className="mt-5 pt-5 border-t border-[#1a1d2e] space-y-2">
            <p className="text-xs text-gray-500 leading-relaxed">
              Our AI is analyzing your video. Processing time depends on the video&apos;s length and complexity.
            </p>
            <p className="text-xs text-gray-600 leading-relaxed">
              Please keep this tab open while your highlights are being generated.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function IconSpinner() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" d="M12 3a9 9 0 109 9" />
    </svg>
  );
}

function IconAlert() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
      />
    </svg>
  );
}

function IconCheckCircle() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
