"use client";

import {
  downloadReel,
  downloadVerticalReel,
  downloadThumbnail,
  downloadResultJson,
} from "../services/api";
import type { JobStats, PipelineJob, ExtendedPipelineResult } from "../types/pipeline";

function parseJobDate(raw: string): string {
  let s = raw.replace(" ", "T");
  if (!/Z$|[+-]\d{2}:?\d{2}$/.test(s)) {
    s += "Z";
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

interface StatsPanelProps {
  jobStats: JobStats | null;
  allJobs: PipelineJob[];
}

interface StatCardProps {
  label: string;
  value: number;
  accentBorder: string;
  accentText: string;
}

function StatCard({ label, value, accentBorder, accentText }: StatCardProps) {
  return (
    <div className={`rounded-xl border ${accentBorder} bg-[#0f1117] p-5`}>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
        {label}
      </p>
      <p className={`text-4xl font-bold mt-2 ${accentText}`}>{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    queued: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
    completed: "bg-green-500/15 text-green-400 border border-green-500/30",
    failed: "bg-red-500/15 text-red-400 border border-red-500/30",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        styles[status] ?? styles.queued
      }`}
    >
      {status}
    </span>
  );
}

function JobResultDetails({ result }: { result: ExtendedPipelineResult }) {
  return (
    <div className="mt-4 pt-4 border-t border-[#1e2030]">
      <div className="flex flex-wrap gap-2">
        {result.final_reel && (
          <button
            onClick={() => downloadReel(result.final_reel)}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
          >
            Open Reel
          </button>
        )}
        {result.vertical_reel && (
          <button
            onClick={() => downloadVerticalReel(result.vertical_reel)}
            className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold"
          >
            Vertical Reel
          </button>
        )}
        {result.thumbnail && (
          <button
            onClick={() => downloadThumbnail(result.thumbnail)}
            className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold"
          >
            Thumbnail
          </button>
        )}
        {result.result_json && (
          <button
            onClick={() => downloadResultJson(result.result_json)}
            className="px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold"
          >
            JSON
          </button>
        )}
      </div>
      <div className="mt-3 flex gap-6 text-xs text-gray-500">
        {result.title && <span className="truncate max-w-xs">{result.title}</span>}
        {result.highlights_found != null && (
          <span>{result.highlights_found} highlights</span>
        )}
        {result.stats?.processing_time != null && (
          <span>{result.stats.processing_time}s</span>
        )}
      </div>
    </div>
  );
}

export function StatsPanel({ jobStats, allJobs }: StatsPanelProps) {
  const recentJobs = allJobs.slice().reverse().slice(0, 20);

  if (!jobStats && recentJobs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Section 2 — System Statistics */}
      {jobStats && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
            System Statistics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="Queued"
              value={jobStats.queued}
              accentBorder="border-yellow-500/25"
              accentText="text-yellow-400"
            />
            <StatCard
              label="Running"
              value={jobStats.running}
              accentBorder="border-blue-500/25"
              accentText="text-blue-400"
            />
            <StatCard
              label="Completed"
              value={jobStats.completed}
              accentBorder="border-green-500/25"
              accentText="text-green-400"
            />
            <StatCard
              label="Failed"
              value={jobStats.failed}
              accentBorder="border-red-500/25"
              accentText="text-red-400"
            />
          </div>
        </div>
      )}

      {/* Section 3 — Recent Jobs */}
      {recentJobs.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
            Recent Jobs
          </h2>
          <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden">
            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-[#0f1117]">
                  <tr className="border-b border-[#1e2030]">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Progress
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Job ID
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#13151e]">
                  {recentJobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3">
                        <StatusPill status={job.status} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-[#1a1d2e] rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-blue-500 h-1.5 rounded-full"
                              style={{ width: `${job.progress ?? 0}%` }}
                            />
                          </div>
                          <span className="text-gray-500 text-xs tabular-nums">
                            {job.progress ?? 0}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {job.created_at ? parseJobDate(job.created_at) : "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                        {job.job_id.slice(0, 8)}…
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
