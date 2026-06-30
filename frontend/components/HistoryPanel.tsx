"use client";

import { downloadReel } from "../services/api";
import type { HistoryItem } from "../types/pipeline";

interface HistoryPanelProps {
  history: HistoryItem[];
}

export function HistoryPanel({ history }: HistoryPanelProps) {
  if (history.length === 0) {
    return null;
  }

  const handleDownloadReel = (reelPath: string | undefined) => {
    downloadReel(reelPath);
  };

  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
        Processing History
      </h2>
      <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden">
        <div className="overflow-x-auto max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#0f1117]">
              <tr className="border-b border-[#1e2030]">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Video
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Highlights
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
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
                          className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
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
    </div>
  );
}
