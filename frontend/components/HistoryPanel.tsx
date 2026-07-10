"use client";

import { downloadReel } from "../services/api";
import type { HistoryItem } from "../types/pipeline";

interface HistoryPanelProps {
  history: HistoryItem[];
  historyLoading?: boolean;
}

function scrollToUpload() {
  document.getElementById("upload-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function HistoryPanel({ history, historyLoading = false }: HistoryPanelProps) {
  const handleDownloadReel = (reelPath: string | undefined) => {
    downloadReel(reelPath);
  };

  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
        Processing History
      </h2>

      {historyLoading ? (
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-8 flex items-center justify-center">
          <div
            className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin"
            aria-label="Loading history"
          />
        </div>
      ) : history.length === 0 ? (
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-10 text-center">
          <svg
            className="w-10 h-10 mx-auto mb-3 text-gray-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.236a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
            />
          </svg>
          <p className="text-white font-semibold text-sm">Upload your first gaming video</p>
          <p className="text-gray-500 text-sm mt-1.5">
            Your processed videos and their highlight counts will show up here.
          </p>
          <button
            onClick={scrollToUpload}
            className="mt-4 inline-block bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
          >
            Upload a video
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden">
          <div className="overflow-x-auto max-h-80 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-[#0f1117]">
                <tr className="border-b border-[#1e2030]">
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Video
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Highlights
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Reel
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#13151e]">
                {history
                  .slice()
                  .reverse()
                  .map((item: HistoryItem) => (
                    <tr
                      key={`${item.video_name}-${item.date}`}
                      className="hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-4 py-3 text-white text-xs max-w-xs truncate">
                        {item.video_name}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {item.date}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs tabular-nums">
                        {item.highlights_count}
                      </td>
                      <td className="px-4 py-3">
                        {item.reel_path ? (
                          <button
                            onClick={() => handleDownloadReel(item.reel_path)}
                            className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
                          >
                            Open
                          </button>
                        ) : (
                          <span className="text-gray-600 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
