"use client";

interface UploadPanelProps {
  selectedFile: File | null;
  loading: boolean;
  onSelectFile: (file: File | null) => void;
  onGenerateHighlights: () => void;
}

export function UploadPanel({
  selectedFile,
  loading,
  onSelectFile,
  onGenerateHighlights,
}: UploadPanelProps) {
  return (
    <div className="mt-10 w-full max-w-2xl">
      <label className="block mb-2 text-lg font-semibold">
        Choose Video
      </label>

      <input
        type="file"
        accept="video/*"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onSelectFile(e.target.files[0]);
          }
        }}
        className="w-full p-3 rounded-lg border-2 border-gray-500 bg-gray-900 text-white"
      />

      {selectedFile && (
        <div className="mt-4 p-4 rounded-lg border border-green-500 bg-gray-900">
          <p className="text-green-400 font-semibold">🎥 Selected Video</p>
          <p className="mt-2 break-all">{selectedFile.name}</p>
        </div>
      )}

      <button
        onClick={onGenerateHighlights}
        disabled={loading || !selectedFile}
        className={`mt-4 w-full bg-green-600 text-white p-4 rounded-lg font-semibold transition-colors ${
          loading
            ? "opacity-50 cursor-wait"
            : !selectedFile
            ? "opacity-50 cursor-not-allowed"
            : "hover:bg-green-700 cursor-pointer"
        }`}
      >
        {loading ? "Generating Highlights..." : "Generate Highlights"}
      </button>
    </div>
  );
}
