"use client";

import {
  downloadReel,
  downloadVerticalReel,
  downloadThumbnail,
  downloadResultJson,
} from "../services/api";
import type { JobStats, PipelineJob, ExtendedPipelineResult } from "../types/pipeline";

interface StatsPanelProps {
  jobStats: JobStats | null;
  allJobs: PipelineJob[];
}

export function StatsPanel({ jobStats, allJobs }: StatsPanelProps) {
  return (
    <>
      {jobStats && (
        <div className="mt-10 w-full max-w-6xl">
          <h2 className="text-4xl font-bold mb-6">📊 Job Queue Dashboard</h2>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-5 rounded-lg border border-cyan-500 bg-gray-900">
              <p>Total Jobs</p>
              <p className="text-4xl font-bold">
                {jobStats.queued +
                  jobStats.running +
                  jobStats.completed +
                  jobStats.failed}
              </p>
            </div>
            <div className="p-5 rounded-lg border border-yellow-500 bg-gray-900">
              <p>Running Jobs</p>
              <p className="text-4xl font-bold">{jobStats.running}</p>
            </div>
            <div className="p-5 rounded-lg border border-green-500 bg-gray-900">
              <p>Completed Jobs</p>
              <p className="text-4xl font-bold">{jobStats.completed}</p>
            </div>
            <div className="p-5 rounded-lg border border-red-500 bg-gray-900">
              <p>Failed Jobs</p>
              <p className="text-4xl font-bold">{jobStats.failed}</p>
            </div>
          </div>
        </div>
      )}

      {allJobs.length > 0 && (
        <div className="mt-10 w-full max-w-6xl">
          <h2 className="text-3xl font-bold mb-4">⚙️ Job Queue</h2>
          <div className="grid gap-3">
            {allJobs
              .slice()
              .reverse()
              .map((job: PipelineJob, index: number) => (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-gray-700 bg-gray-900"
                >
                  <div className="grid md:grid-cols-5 gap-4">
                    <div>
                      <p className="text-gray-400">Job ID</p>
                      <p className="break-all">{job.job_id}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Status</p>
                      <p>{job.status}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Progress</p>
                      <p>{job.progress}%</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Created</p>
                      <p>{job.created_at || "-"}</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Completed</p>
                      <p>{job.updated_at || "-"}</p>
                    </div>
                  </div>

                  {job.status === "completed" && job.result && (
                    <JobResultDetails result={job.result} />
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </>
  );
}

function JobResultDetails({ result }: { result: ExtendedPipelineResult }) {
  return (
    <div className="mt-6 border-t border-gray-700 pt-4">
      <div className="grid md:grid-cols-4 gap-3">
        {result.final_reel && (
          <button
            onClick={() => downloadReel(result.final_reel)}
            className="bg-blue-600 hover:bg-blue-700 p-3 rounded-lg font-semibold"
          >
            🎬 Open Reel
          </button>
        )}
        {result.vertical_reel && (
          <button
            onClick={() => downloadVerticalReel(result.vertical_reel)}
            className="bg-purple-600 hover:bg-purple-700 p-3 rounded-lg font-semibold"
          >
            📱 Open Vertical Reel
          </button>
        )}
        {result.thumbnail && (
          <button
            onClick={() => downloadThumbnail(result.thumbnail)}
            className="bg-cyan-600 hover:bg-cyan-700 p-3 rounded-lg font-semibold"
          >
            🖼 Open Thumbnail
          </button>
        )}
        {result.result_json && (
          <button
            onClick={() => downloadResultJson(result.result_json)}
            className="bg-orange-600 hover:bg-orange-700 p-3 rounded-lg font-semibold"
          >
            📄 Open JSON
          </button>
        )}
      </div>
      <div className="mt-4 grid md:grid-cols-3 gap-4">
        <div>
          <p className="text-gray-400">Title</p>
          <p className="font-semibold">{result.title || "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">Highlights</p>
          <p className="font-semibold">{result.highlights_found || "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">Processing Time</p>
          <p className="font-semibold">
            {result.stats?.processing_time || 0}s
          </p>
        </div>
      </div>
    </div>
  );
}
