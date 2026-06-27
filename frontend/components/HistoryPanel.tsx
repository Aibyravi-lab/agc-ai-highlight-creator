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
    <div className="mt-12 w-full max-w-6xl">
      <h2 className="text-4xl font-bold mb-6">📜 Processing History</h2>
      <div className="grid gap-4">
        {history
          .slice()
          .reverse()
          .map((item: HistoryItem, index: number) => (
            <div
              key={index}
              className="p-5 rounded-lg border border-gray-700 bg-gray-900"
            >
              <div className="grid md:grid-cols-4 gap-4 items-center">
                <div>
                  <p className="text-gray-400">Video Name</p>
                  <p className="font-semibold break-all">{item.video_name}</p>
                </div>
                <div>
                  <p className="text-gray-400">Date</p>
                  <p>{item.date}</p>
                </div>
                <div>
                  <p className="text-gray-400">Highlights Found</p>
                  <p>{item.highlights_count}</p>
                </div>
                <div>
                  {item.reel_path && (
                    <button
                      onClick={() => handleDownloadReel(item.reel_path)}
                      className="w-full bg-blue-600 hover:bg-blue-700 p-3 rounded-lg font-semibold"
                    >
                      🎬 Open Reel
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
