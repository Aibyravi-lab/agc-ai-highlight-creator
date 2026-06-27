"use client";

import {
  downloadReel,
  downloadVerticalReel,
  getReelUrl,
  getVerticalReelUrl,
} from "../services/api";
import type { ExtendedPipelineResult } from "../types/pipeline";

interface DownloadPanelProps {
  result: ExtendedPipelineResult | null;
}

export function DownloadPanel({ result }: DownloadPanelProps) {
  if (!result) {
    return null;
  }

  const handleDownloadReel = () => {
    downloadReel(result.final_reel);
  };

  const handleDownloadVertical = () => {
    downloadVerticalReel(result.vertical_reel);
  };

  return (
    <div className="mt-6 grid gap-4 md:grid-cols-2">
      <div className="border border-blue-500 rounded-lg p-5 bg-gray-900">
        <h3 className="text-xl font-bold text-blue-400">🎯 Highlights Found</h3>
        <p className="text-4xl mt-3 font-bold">{result.highlights_found}</p>
      </div>

      <div className="border border-blue-500 rounded-lg p-5 bg-gray-900">
        <h3 className="text-xl font-bold text-blue-400">🎬 Final Reel Preview</h3>
        <video controls className="mt-4 w-full rounded-lg">
          <source src={getReelUrl(result.final_reel)} type="video/mp4" />
        </video>
        <button
          onClick={handleDownloadReel}
          className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-semibold"
        >
          ⬇ Open Reel
        </button>
        <button
          onClick={handleDownloadVertical}
          className="mt-3 w-full bg-purple-600 hover:bg-purple-700 text-white p-3 rounded-lg font-semibold"
        >
          📱 Open Vertical Reel
        </button>
      </div>
    </div>
  );
}
