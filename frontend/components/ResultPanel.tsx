"use client";

import {
  downloadThumbnail,
  downloadResultJson,
  getThumbnailUrl,
  getClipUrl,
} from "../services/api";
import type {
  ExtendedPipelineResult,
  HighlightItem,
} from "../types/pipeline";

interface ResultPanelProps {
  result: ExtendedPipelineResult | null;
}

export function ResultPanel({ result }: ResultPanelProps) {
  if (!result) {
    return null;
  }

  const copyToClipboard = (text: string, message: string) => {
    navigator.clipboard.writeText(text);
    alert(message);
  };

  const handleDownloadThumbnail = () => {
    downloadThumbnail(result.thumbnail);
  };

  const handleDownloadResultJson = () => {
    downloadResultJson(result.result_json);
  };

  return (
    <div className="mt-12 w-full max-w-6xl">
      <h2 className="text-4xl font-bold mb-6">Results</h2>

      {result.stats && (
        <div className="mb-6 p-6 rounded-lg border border-yellow-500 bg-gray-900">
          <h3 className="text-2xl font-bold text-yellow-400 mb-4">
            📊 Processing Stats
          </h3>
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <p className="text-gray-400">Video Duration</p>
              <p className="text-2xl font-bold">
                {result.stats.video_duration}s
              </p>
            </div>
            <div>
              <p className="text-gray-400">Frames Analyzed</p>
              <p className="text-2xl font-bold">
                {result.stats.frames_analyzed}
              </p>
            </div>
            <div>
              <p className="text-gray-400">Highlights Found</p>
              <p className="text-2xl font-bold">
                {result.stats.highlights_found}
              </p>
            </div>
            <div>
              <p className="text-gray-400">Processing Time</p>
              <p className="text-2xl font-bold">
                {result.stats.processing_time}s
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 p-6 border border-purple-500 rounded-lg bg-gray-900">
        <h3 className="text-2xl font-bold text-purple-400">🔥 Viral Package</h3>

        <div className="mt-4">
          <p>
            <strong>Title:</strong>
          </p>
          <p className="mt-2">{result.title}</p>
          <button
            onClick={() =>
              copyToClipboard(result.title || "", "Title Copied")
            }
            className="mt-2 bg-yellow-600 px-4 py-2 rounded"
          >
            📋 Copy Title
          </button>
        </div>

        <div className="mt-6">
          <p>
            <strong>Description:</strong>
          </p>
          <p className="mt-2">{result.description}</p>
          <button
            onClick={() =>
              copyToClipboard(
                result.description || "",
                "Description Copied"
              )
            }
            className="mt-2 bg-green-600 px-4 py-2 rounded"
          >
            📋 Copy Description
          </button>
          <button
            onClick={handleDownloadResultJson}
            className="mt-4 w-full bg-orange-600 hover:bg-orange-700 text-white p-3 rounded-lg font-semibold"
          >
            📄 Download Results JSON
          </button>
        </div>

        <div className="mt-6">
          <p>
            <strong>Hashtags:</strong>
          </p>
          <p className="mt-2">{result.hashtags?.join(" ")}</p>
          <button
            onClick={() =>
              copyToClipboard(
                result.hashtags?.join(" ") || "",
                "Hashtags Copied"
              )
            }
            className="mt-2 bg-pink-600 px-4 py-2 rounded"
          >
            📋 Copy Hashtags
          </button>
        </div>
      </div>

      {result.social_exports && (
        <div className="mt-6 p-6 rounded-lg border border-cyan-500 bg-gray-900">
          <h3 className="text-2xl font-bold text-cyan-400 mb-4">
            🚀 Social Media Exports
          </h3>
          <div className="grid gap-6 md:grid-cols-3">
            <div className="p-4 rounded-lg border border-red-500 bg-black">
              <h4 className="text-xl font-bold text-red-400">📺 YouTube</h4>
              <textarea
                readOnly
                value={result.social_exports?.youtube?.description || ""}
                className="w-full h-48 mt-3 p-3 rounded bg-gray-950 text-sm"
              />
              <button
                onClick={() =>
                  copyToClipboard(
                    result.social_exports?.youtube?.description || "",
                    "YouTube Copied"
                  )
                }
                className="mt-3 w-full bg-red-600 hover:bg-red-700 p-2 rounded"
              >
                Copy YouTube
              </button>
            </div>

            <div className="p-4 rounded-lg border border-pink-500 bg-black">
              <h4 className="text-xl font-bold text-pink-400">📸 Instagram</h4>
              <textarea
                readOnly
                value={result.social_exports?.instagram?.caption || ""}
                className="w-full h-48 mt-3 p-3 rounded bg-gray-950 text-sm"
              />
              <button
                onClick={() =>
                  copyToClipboard(
                    result.social_exports?.instagram?.caption || "",
                    "Instagram Copied"
                  )
                }
                className="mt-3 w-full bg-pink-600 hover:bg-pink-700 p-2 rounded"
              >
                Copy Instagram
              </button>
            </div>

            <div className="p-4 rounded-lg border border-cyan-500 bg-black">
              <h4 className="text-xl font-bold text-cyan-400">🎵 TikTok</h4>
              <textarea
                readOnly
                value={result.social_exports?.tiktok?.caption || ""}
                className="w-full h-48 mt-3 p-3 rounded bg-gray-950 text-sm"
              />
              <button
                onClick={() =>
                  copyToClipboard(
                    result.social_exports?.tiktok?.caption || "",
                    "TikTok Copied"
                  )
                }
                className="mt-3 w-full bg-cyan-600 hover:bg-cyan-700 p-2 rounded"
              >
                Copy TikTok
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 p-6 border border-cyan-500 rounded-lg bg-gray-900">
        <h3 className="text-2xl font-bold text-cyan-400">🖼 Best Thumbnail</h3>
        <button
          onClick={handleDownloadThumbnail}
          className="mt-4 w-full bg-cyan-600 hover:bg-cyan-700 text-white p-3 rounded-lg font-semibold"
        >
          ⬇ Download Thumbnail
        </button>
        <img
          src={getThumbnailUrl(result.thumbnail)}
          alt="thumbnail"
          className="mt-4 rounded-lg max-h-[500px] object-cover mx-auto"
        />
      </div>

      {result.all_highlights && result.all_highlights.length > 0 && (
        <div className="mt-8">
          <h3 className="text-3xl font-bold text-green-400 mb-6">
            🎯 Top Highlights Gallery
          </h3>
          <div className="grid gap-6 md:grid-cols-2">
            {result.all_highlights.map((highlight: HighlightItem, index: number) => (
              <div
                key={index}
                className="p-5 rounded-lg border border-green-500 bg-gray-900"
              >
                <h4 className="text-xl font-bold text-green-400 mb-3">
                  Highlight #{index + 1}
                </h4>
                <video controls className="w-full rounded-lg">
                  <source
                    src={getClipUrl(highlight.clip_path)}
                    type="video/mp4"
                  />
                </video>
                <div className="mt-4 space-y-2">
                  <p>
                    <strong>Timestamp:</strong> {highlight.timestamp} sec
                  </p>
                  <p>
                    <strong>Action:</strong> {highlight.action}
                  </p>
                  <p>
                    <strong>Score:</strong> {(highlight.score * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
