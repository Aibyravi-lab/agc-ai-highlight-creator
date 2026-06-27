"use client";

interface ProgressPanelProps {
  loading: boolean;
  progress: number;
  progressStatus: string;
  error?: string | null;
  onClearError?: () => void;
}

export function ProgressPanel({
  loading,
  progress,
  progressStatus,
  error,
  onClearError,
}: ProgressPanelProps) {
  if (!loading && !error) {
    return null;
  }

  return (
    <>
      {error && (
        <div className="w-full max-w-6xl mt-6 border border-red-500 p-6 rounded-lg bg-red-900/20">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-red-400 font-semibold text-lg">❌ Processing Failed</p>
              <p className="mt-3 text-red-200">{error}</p>
            </div>
            {onClearError && (
              <button
                onClick={onClearError}
                className="ml-4 bg-red-600 hover:bg-red-700 px-6 py-2 rounded text-white font-semibold whitespace-nowrap"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      {loading && !error && (
        <div className="w-full max-w-6xl mt-6 border border-blue-500 p-6 rounded-lg bg-blue-900/10">
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <div>
                <p className="text-gray-400 text-sm uppercase tracking-wide">Processing Status</p>
                <p className="text-xl font-semibold text-blue-400 mt-1">{progressStatus}</p>
              </div>
              <div className="text-right">
                <p className="text-4xl font-bold text-blue-400">{progress}%</p>
              </div>
            </div>

            <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden shadow-lg">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-400 h-3 rounded-full transition-all duration-300 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]"
                style={{
                  width: `${progress}%`,
                }}
              />
            </div>
          </div>

          <div className="mt-4 flex items-center text-gray-400 text-sm">
            <div className="w-2 h-2 bg-blue-400 rounded-full mr-2 animate-pulse" />
            <span>Processing your video...</span>
          </div>
        </div>
      )}
    </>
  );
}
