"use client";

import { useState } from "react";

export default function Home() {
  const [videoPath, setVideoPath] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const processVideo = async () => {
    if (!videoPath) {
      alert("Enter video path");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `http://localhost:8000/pipeline/process?video_path=${encodeURIComponent(
          videoPath
        )}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();
      setResult(data.data);
    } catch (error) {
      console.error(error);
      alert("Backend API failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center p-10">
      <h1 className="text-6xl font-bold">🎮 AGC</h1>

      <p className="mt-4 text-3xl">
        AI Gaming Highlight Creator
      </p>

      <div className="mt-10 w-full max-w-2xl">
        <input
          type="text"
          placeholder="storage/uploads/0616(1).mp4"
          value={videoPath}
          onChange={(e) => setVideoPath(e.target.value)}
          className="w-full p-4 rounded-lg border-2 border-gray-500 bg-gray-900 text-white placeholder-gray-400"
        />

        <button
          onClick={processVideo}
          disabled={loading}
          className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-lg font-semibold"
        >
          {loading ? "Processing..." : "Process Video"}
        </button>
      </div>

      {result && (
        <div className="mt-12 w-full max-w-4xl">
          <h2 className="text-4xl font-bold mb-6">
            Results
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="border border-green-500 rounded-lg p-5 bg-gray-900">
              <h3 className="text-xl font-bold text-green-400">
                🎯 Highlights Found
              </h3>

              <p className="text-4xl mt-3 font-bold">
                {result.highlights_found}
              </p>
            </div>

            <div className="border border-blue-500 rounded-lg p-5 bg-gray-900">
              <h3 className="text-xl font-bold text-blue-400">
                🎬 Final Reel
              </h3>

              <p className="mt-3 break-all">
                {result.final_reel}
              </p>
            </div>
          </div>

          <div className="mt-6 p-6 border border-yellow-500 rounded-lg bg-gray-900">
            <h3 className="text-2xl font-bold text-yellow-400">
              🏆 Best Highlight
            </h3>

            <div className="mt-4 space-y-3">
              <p>
                <strong>Timestamp:</strong>{" "}
                {result.best_highlight?.timestamp} sec
              </p>

              <p>
                <strong>Action:</strong>{" "}
                {result.best_highlight?.action}
              </p>

              <p>
                <strong>Score:</strong>{" "}
                {result.best_highlight?.score
                  ? (result.best_highlight.score * 100).toFixed(2)
                  : 0}
                %
              </p>

              <p className="break-all">
                <strong>Clip:</strong>{" "}
                {result.best_highlight?.clip_path}
              </p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}