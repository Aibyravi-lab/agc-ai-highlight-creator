"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { MAX_UPLOAD_SIZE_MB, MAX_VIDEO_DURATION_MINUTES } from "../utils/uploadLimits";

interface UploadPanelProps {
  selectedFile: File | null;
  loading: boolean;
  progressStatus: string;
  onSelectFile: (file: File | null) => void;
  onGenerateHighlights: () => void;
  fileInputKey: number;
  creditsRemaining: number;
  isPro?: boolean;
  subscriptionLoading?: boolean;
}

const SUPPORTED_FORMATS_LABEL = "MP4 • MOV • AVI • MKV";

function formatFileSize(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / 1024 ** exponent;
  const decimals = exponent === 0 || value >= 10 ? 0 : 1;
  return `${value.toFixed(decimals)} ${units[exponent]}`;
}

function buttonLabel(loading: boolean, progressStatus: string): string {
  if (!loading) return "Generate Highlights";
  return progressStatus.toLowerCase().startsWith("uploading") ? "Uploading..." : "Processing...";
}

export function UploadPanel({
  selectedFile,
  loading,
  progressStatus,
  onSelectFile,
  onGenerateHighlights,
  fileInputKey,
  creditsRemaining,
  isPro = false,
  subscriptionLoading = false,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const isUploading = loading && progressStatus.toLowerCase().startsWith("uploading");
  const outOfCredits = !subscriptionLoading && !isPro && creditsRemaining <= 0;

  const handleFiles = (files: FileList | null) => {
    if (files && files.length > 0) {
      onSelectFile(files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl">
      <label className="block mb-3 text-lg font-semibold text-white">Upload Your Video</label>

      <input
        key={fileInputKey}
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        disabled={outOfCredits}
        onChange={(e) => handleFiles(e.target.files)}
      />

      {/* Drop zone */}
      <div className="relative">
        <div
          role="button"
          tabIndex={outOfCredits ? -1 : 0}
          aria-disabled={outOfCredits}
          aria-label="Upload video: drag and drop or click to browse"
          onClick={() => {
            if (!outOfCredits) inputRef.current?.click();
          }}
          onKeyDown={(e) => {
            if (outOfCredits) return;
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            if (outOfCredits) return;
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            if (outOfCredits) return;
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`flex flex-col items-center justify-center text-center rounded-2xl border-2 border-dashed px-6 py-14 transition-colors ${
            outOfCredits
              ? "opacity-50 cursor-not-allowed pointer-events-none border-[#2a2d3e] bg-[#0d0e14]"
              : isDragging
              ? "border-green-500 bg-green-500/5 cursor-pointer"
              : "border-[#2a2d3e] bg-[#0d0e14] hover:border-green-500/50 hover:bg-[#0f1117] cursor-pointer"
          }`}
        >
          <div className="w-16 h-16 rounded-2xl bg-green-500/10 flex items-center justify-center text-green-400 mb-5">
            <IconUploadCloud />
          </div>
          <p className="text-white font-semibold text-base">Drag &amp; Drop your video here</p>
          <p className="text-gray-500 text-sm mt-1.5">or click to browse your files</p>
        </div>

        {outOfCredits && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center rounded-2xl bg-[#0d0e14]/85 px-6">
            <p className="text-white font-semibold text-base">🔒 Upload disabled</p>
            <p className="text-gray-400 text-sm mt-1.5 max-w-xs">
              Upgrade to Pro to continue generating AI highlights.
            </p>
          </div>
        )}
      </div>

      {/* Supported formats / limits */}
      <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 text-xs text-gray-500">
        <span>
          Supported formats: <span className="text-gray-400">{SUPPORTED_FORMATS_LABEL}</span>
        </span>
        <span>Maximum upload size: {MAX_UPLOAD_SIZE_MB} MB</span>
      </div>

      <p className="mt-1.5 text-xs text-gray-500">
        Maximum video duration: {MAX_VIDEO_DURATION_MINUTES} minutes
      </p>

      {/* Selected file summary */}
      {selectedFile && (
        <div className="mt-5 rounded-2xl border border-[#1a1d2e] bg-[#0d0e14] p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-green-500/10 flex items-center justify-center text-green-400 flex-shrink-0">
            <IconFilm />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white truncate">{selectedFile.name}</p>
            <p className="text-xs text-gray-500 mt-0.5">{formatFileSize(selectedFile.size)}</p>
          </div>
          {!loading && (
            <span className="flex items-center gap-1.5 text-xs text-green-400 font-medium flex-shrink-0">
              <IconCheck />
              Ready to upload
            </span>
          )}
        </div>
      )}

      <button
        onClick={onGenerateHighlights}
        disabled={loading || !selectedFile || outOfCredits || subscriptionLoading}
        className={`mt-5 w-full text-white p-4 rounded-xl font-semibold transition-colors ${
          loading
            ? "bg-green-600/50 cursor-wait"
            : !selectedFile || outOfCredits || subscriptionLoading
            ? "bg-green-600/50 cursor-not-allowed"
            : "bg-green-600 hover:bg-green-700 cursor-pointer"
        }`}
      >
        {buttonLabel(loading, progressStatus)}
      </button>

      {subscriptionLoading && !loading && (
        <div className="mt-4 flex justify-center">
          <div className="h-3 w-40 rounded-full bg-[#1a1d2e] animate-pulse" />
        </div>
      )}

      {outOfCredits && !loading && (
        <div className="mt-4 text-center">
          <p className="text-xs text-yellow-400 leading-relaxed">
            You&apos;ve used all your free credits.
            <br />
            Upgrade to continue generating highlights.
          </p>
          <Link
            href="/pricing"
            className="mt-3 inline-block bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors"
          >
            Upgrade to Pro
          </Link>
        </div>
      )}

      {isUploading && (
        <p className="mt-4 text-xs text-gray-500 text-center leading-relaxed">
          Uploading your video...
          <br />
          Please keep this tab open until the upload completes.
        </p>
      )}
    </div>
  );
}

function IconUploadCloud() {
  return (
    <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7.5 15a4.5 4.5 0 01-1.406-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 15h-1.5m-5.25-6v9m0-9l3 3m-3-3l-3 3"
      />
    </svg>
  );
}

function IconFilm() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125V6.375m0 13.125A1.125 1.125 0 012.25 18.375M2.25 18.375V6.375m0 0A1.125 1.125 0 013.375 5.25h17.25a1.125 1.125 0 011.125 1.125M21.75 18.375V6.375m0 12A1.125 1.125 0 0120.625 19.5h-1.5c-.621 0-1.125-.504-1.125-1.125m3.75-12A1.125 1.125 0 0020.625 5.25H3.375m0 0h17.25M6 18.375V5.625m12 12.75V5.625M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H13.5m-1.5 3H13.5m-1.5 3H13.5"
      />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}
