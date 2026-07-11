"use client";

import { useState } from "react";
import {
  downloadReel,
  downloadVerticalReel,
  downloadThumbnail,
  downloadResultJson,
} from "../services/api";
import { track } from "../services/analytics";
import { useAuthedMediaUrl } from "../hooks/useAuthedMediaUrl";
import { selectDisplayReasons } from "../utils/highlightReasons";
import type { ExtendedPipelineResult, HighlightItem } from "../types/pipeline";

interface ResultPanelProps {
  result: ExtendedPipelineResult | null;
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="shrink-0 px-3 py-1 rounded-md text-xs font-semibold border transition-colors
        border-[#2a2d3e] text-gray-400 hover:text-white hover:border-[#3a3d4e]"
    >
      {copied ? "Copied!" : label}
    </button>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-[#0a0b0f] border border-[#1a1d2e] px-4 py-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white tabular-nums">{value}</p>
    </div>
  );
}

function DownloadButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg bg-[#1a1d2e] hover:bg-[#1e2235] text-sm font-medium text-white border border-[#2a2d3e] transition-colors"
    >
      {label}
    </button>
  );
}

function HighlightClipPreview({ clipPath }: { clipPath?: string }) {
  const clipUrl = useAuthedMediaUrl(clipPath);

  if (!clipPath) return null;

  return (
    <video controls className="w-full max-h-[270px] rounded-md mb-3">
      {clipUrl && <source src={clipUrl} type="video/mp4" />}
    </video>
  );
}

export function ResultPanel({ result }: ResultPanelProps) {
  const reelUrl = useAuthedMediaUrl(result?.final_reel);

  if (!result) return null;

  const hasReel = !!result.final_reel;
  const hasVertical = !!result.vertical_reel;
  const hasThumbnail = !!result.thumbnail;
  const hasResultJson = !!result.result_json;
  const hasAnyDownload = hasReel || hasVertical || hasThumbnail || hasResultJson;
  const hasHighlights =
    result.all_highlights && result.all_highlights.length > 0;

  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#1a1d2e]">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Results
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* Part 4 — Video Embed (only when final_reel exists) */}
        {hasReel && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
              Preview
            </p>
            <video controls className="w-full max-h-[480px] rounded-lg">
              {reelUrl && <source src={reelUrl} type="video/mp4" />}
            </video>
          </div>
        )}

        {/* Part 1 — Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Highlights Found" value={result.highlights_found ?? 0} />
          {result.stats?.video_duration != null && (
            <StatCard
              label="Duration"
              value={`${result.stats.video_duration}s`}
            />
          )}
          {result.stats?.frames_analyzed != null && (
            <StatCard
              label="Frames Analyzed"
              value={result.stats.frames_analyzed}
            />
          )}
          {result.stats?.processing_time != null && (
            <StatCard
              label="Processed In"
              value={`${result.stats.processing_time}s`}
            />
          )}
        </div>

        {/* Part 2 — Download Buttons (conditional on file existence) */}
        {hasAnyDownload && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
              Downloads
            </p>
            <div className="flex flex-wrap gap-2">
              {hasReel && (
                <DownloadButton
                  label="Download Reel"
                  onClick={() => {
                    track("Download Reel");
                    downloadReel(result.final_reel);
                  }}
                />
              )}
              {hasVertical && (
                <DownloadButton
                  label="Download Vertical Reel"
                  onClick={() => {
                    track("Download Reel");
                    downloadVerticalReel(result.vertical_reel);
                  }}
                />
              )}
              {hasThumbnail && (
                <DownloadButton
                  label="Download Thumbnail"
                  onClick={() => {
                    track("Download Thumbnail");
                    downloadThumbnail(result.thumbnail);
                  }}
                />
              )}
              {hasResultJson && (
                <DownloadButton
                  label="Download Results JSON"
                  onClick={() => downloadResultJson(result.result_json)}
                />
              )}
            </div>
          </div>
        )}

        {/* Part 1 + Part 3 — Title, Description, Hashtags with Copy buttons */}
        <div className="space-y-3">
          {result.title && (
            <div className="rounded-lg bg-[#0a0b0f] border border-[#1a1d2e] p-4">
              <div className="flex items-center justify-between gap-4 mb-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
                  Title
                </p>
                <CopyButton text={result.title} label="Copy Title" />
              </div>
              <p className="text-sm text-white leading-relaxed">{result.title}</p>
            </div>
          )}

          {result.description && (
            <div className="rounded-lg bg-[#0a0b0f] border border-[#1a1d2e] p-4">
              <div className="flex items-center justify-between gap-4 mb-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
                  Description
                </p>
                <CopyButton
                  text={result.description}
                  label="Copy Description"
                />
              </div>
              <p className="text-sm text-white leading-relaxed whitespace-pre-line">
                {result.description}
              </p>
            </div>
          )}

          {result.hashtags && result.hashtags.length > 0 && (
            <div className="rounded-lg bg-[#0a0b0f] border border-[#1a1d2e] p-4">
              <div className="flex items-center justify-between gap-4 mb-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
                  Hashtags
                </p>
                <CopyButton
                  text={result.hashtags.join(" ")}
                  label="Copy Hashtags"
                />
              </div>
              <p className="text-sm text-blue-400 leading-relaxed">
                {result.hashtags.join(" ")}
              </p>
            </div>
          )}
        </div>

        {/* Highlights Gallery */}
        {hasHighlights && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
              Highlight Clips
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {result.all_highlights!.map(
                (highlight: HighlightItem, index: number) => {
                  const displayReasons = selectDisplayReasons(
                    highlight.explanation?.reasons
                  );

                  return (
                    <div
                      key={index}
                      className="rounded-lg bg-[#0a0b0f] border border-[#1a1d2e] p-4"
                    >
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                        Clip {index + 1}
                      </p>
                      <HighlightClipPreview clipPath={highlight.clip_path} />
                      <div className="space-y-1 text-sm text-gray-400">
                        <p>
                          <span className="text-gray-600">Timestamp</span>{" "}
                          {highlight.timestamp}s
                        </p>
                        {highlight.action && (
                          <p>
                            <span className="text-gray-600">Action</span>{" "}
                            {highlight.action}
                          </p>
                        )}
                        <p>
                          <span className="text-gray-600">Score</span>{" "}
                          {(highlight.score * 100).toFixed(1)}%
                        </p>
                      </div>
                      {displayReasons.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-[#1a1d2e]">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">
                            Why this moment?
                          </p>
                          <ul className="space-y-1 text-sm text-gray-400">
                            {displayReasons.map((reason) => (
                              <li key={reason} className="flex items-start gap-2">
                                <span className="text-green-500 mt-0.5">✓</span>
                                <span>{reason}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                }
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
