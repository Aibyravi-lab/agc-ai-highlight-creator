"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [result, setResult] =
    useState<any>(null);

  const [loading, setLoading] =
    useState(false);

  const [progress, setProgress] =
  useState(0);

  const [progressStatus, setProgressStatus] =
    useState("");

  const [history, setHistory] =
    useState<any[]>([]);  
  const generateHighlights = async () => {

  if (!selectedFile) {

    alert(
      "Please select a video"
    );

    return;

  }

  setLoading(true);

  setResult(null);

  setProgress(0);

  setProgressStatus(
    "Starting..."
  );

  try {

    const formData =
      new FormData();

    formData.append(
      "file",
      selectedFile
    );

    const uploadResponse =
      await fetch(
        "http://localhost:8000/upload/",
        {
          method: "POST",
          body: formData,
        }
      );

    const uploadData =
      await uploadResponse.json();

    const uploadedPath =
      uploadData.location;

    const processResponse =
      await fetch(
        `http://localhost:8000/pipeline/process?video_path=${encodeURIComponent(
          uploadedPath
        )}`,
        {
          method: "POST",
        }
      );

    const processData =
      await processResponse.json();

    setResult(
      processData.data
    );

    await loadHistory();

    setProgress(100);

    setProgressStatus(
      "Completed"
    );

  } catch (error) {

    console.error(
      error
    );

    alert(
      "Processing failed"
    );

  } finally {

    setLoading(
      false
    );

  }

};
  const getVideoUrl = () => {
    if (!result?.final_reel)
      return "";

    const normalizedPath =
      result.final_reel.replaceAll(
        "\\",
        "/"
      );

    return `http://localhost:8000/${normalizedPath}`;
  };

  const getVerticalVideoUrl =
    () => {
      if (
        !result?.vertical_reel
      )
        return "";

      const normalizedPath =
        result.vertical_reel.replaceAll(
          "\\",
          "/"
        );

      return `http://localhost:8000/${normalizedPath}`;
    };

  const getThumbnailUrl =
    () => {
      if (!result?.thumbnail)
        return "";

      const normalizedPath =
        result.thumbnail.replaceAll(
          "\\",
          "/"
        );

      return `http://localhost:8000/${normalizedPath}`;
    };

  const getClipUrl = (
    clipPath: string
  ) => {
    if (!clipPath)
      return "";

    const normalizedPath =
      clipPath.replaceAll(
        "\\",
        "/"
      );

    return `http://localhost:8000/${normalizedPath}`;
  };

  const downloadReel = () => {
    const videoUrl =
      getVideoUrl();

    if (!videoUrl) {
      alert(
        "No reel available"
      );
      return;
    }

    window.open(
      videoUrl,
      "_blank"
    );
  };

  const downloadVerticalReel =
    () => {
      const videoUrl =
        getVerticalVideoUrl();

      if (!videoUrl) {
        alert(
          "No vertical reel available"
        );
        return;
      }

      window.open(
        videoUrl,
        "_blank"
      );
    };

  const copyToClipboard = (
    text: string,
    message: string
  ) => {
    navigator.clipboard.writeText(
      text
    );

    alert(message);
  };
  const downloadResultsJson =
  () => {

    if (
      !result?.result_json
    ) {

      alert(
        "Results JSON not found"
      );

      return;

    }

    const normalizedPath =
      result.result_json.replaceAll(
        "\\",
        "/"
      );

    window.open(
      `http://localhost:8000/${normalizedPath}`,
      "_blank"
    );

  };

const loadHistory =
  async () => {

    try {

      const response =
        await fetch(
          "http://localhost:8000/history/"
        );

      const data =
        await response.json();

      setHistory(
        data.data || []
      );

    } catch (error) {

      console.error(
        "History Load Failed",
        error
      );

    }

  };

const loadProgress =
  async () => {

    try {

      const response =
        await fetch(
          "http://localhost:8000/pipeline/progress"
        );

      const data =
        await response.json();

      setProgress(
        data.data?.progress || 0
      );

      setProgressStatus(
        data.data?.status || ""
      );

    } catch (error) {

      console.error(
        "Progress Load Failed",
        error
      );

    }

  };

useEffect(() => {

  loadHistory();

  const interval =
    setInterval(() => {

      loadProgress();

    }, 2000);

  return () =>
    clearInterval(
      interval
    );

}, []);

return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center p-10">

      <h1 className="text-6xl font-bold">
        🎮 AGC
      </h1>

      <p className="mt-4 text-3xl">
        AI Gaming Highlight Creator
      </p>

      <div className="mt-10 w-full max-w-2xl">

        <label className="block mb-2 text-lg font-semibold">
          Choose Video
        </label>

        <input
          type="file"
          accept="video/*"
          onChange={(e) => {
            if (
              e.target.files &&
              e.target.files.length >
                0
            ) {
              setSelectedFile(
                e.target.files[0]
              );
            }
          }}
          className="w-full p-3 rounded-lg border-2 border-gray-500 bg-gray-900 text-white"
        />

        {selectedFile && (
          <div className="mt-4 p-4 rounded-lg border border-green-500 bg-gray-900">

            <p className="text-green-400 font-semibold">
              🎥 Selected Video
            </p>

            <p className="mt-2 break-all">
              {selectedFile.name}
            </p>

          </div>
        )}

        <button
          onClick={
            generateHighlights
          }
          disabled={loading}
          className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg font-semibold disabled:opacity-50"
        >
          {loading
            ? "Generating Highlights..."
            : "Generate Highlights"}
        </button>

        
        {loading && (

          <div className="mt-4 p-4 rounded-lg border border-green-500 bg-gray-900">

            <div className="flex justify-between mb-2">

              <span>
                {progressStatus}
              </span>

              <span>
                {progress}%
              </span>

            </div>

            <div className="w-full bg-gray-700 rounded-full h-4">

              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-500"
                style={{
                  width: `${progress}%`
                }}
              />

            </div>

          </div>

        )}
      </div>
        {/* Processing History */}

{history.length > 0 && (

  <div className="mt-12 w-full max-w-6xl">

    <h2 className="text-4xl font-bold mb-6">
      📜 Processing History
    </h2>

    <div className="grid gap-4">

      {history
        .slice()
        .reverse()
        .map(
          (
            item: any,
            index: number
          ) => (

            <div
              key={index}
              className="p-5 rounded-lg border border-gray-700 bg-gray-900"
            >

              <div className="grid md:grid-cols-4 gap-4 items-center">

                <div>

                  <p className="text-gray-400">
                    Video Name
                  </p>

                  <p className="font-semibold break-all">
                    {item.video_name}
                  </p>

                </div>

                <div>

                  <p className="text-gray-400">
                    Date
                  </p>

                  <p>
                    {item.date}
                  </p>

                </div>

                <div>

                  <p className="text-gray-400">
                    Highlights
                  </p>

                  <p className="text-xl font-bold text-green-400">
                    {item.highlights_count || 0}
                  </p>

                </div>

                <div>

                  {item.reel_path && (

                    <button
                      onClick={() =>
                        window.open(
                          `http://localhost:8000/${item.reel_path.replaceAll(
                            "\\",
                            "/"
                          )}`,
                          "_blank"
                        )
                      }
                      className="w-full bg-blue-600 hover:bg-blue-700 p-3 rounded-lg font-semibold"
                    >
                      🎬 Open Reel
                    </button>

                  )}

                </div>

              </div>

            </div>

          )
        )}

    </div>

  </div>

)}
      {result && (
        <div className="mt-12 w-full max-w-6xl">

          <h2 className="text-4xl font-bold mb-6">
            Results
          </h2>
          {result.stats && (

            <div className="mb-6 p-6 rounded-lg border border-yellow-500 bg-gray-900">

              <h3 className="text-2xl font-bold text-yellow-400 mb-4">
                📊 Processing Stats
              </h3>

              <div className="grid gap-4 md:grid-cols-4">

                <div>
                  <p className="text-gray-400">
                    Video Duration
                  </p>

                  <p className="text-2xl font-bold">
                    {result.stats.video_duration}s
                  </p>
                </div>

                <div>
                  <p className="text-gray-400">
                    Frames Analyzed
                  </p>

                  <p className="text-2xl font-bold">
                    {result.stats.frames_analyzed}
                  </p>
                </div>

                <div>
                  <p className="text-gray-400">
                    Highlights Found
                  </p>

                  <p className="text-2xl font-bold">
                    {result.stats.highlights_found}
                  </p>
                </div>

                <div>
                  <p className="text-gray-400">
                    Processing Time
                  </p>

                  <p className="text-2xl font-bold">
                    {result.stats.processing_time}s
                  </p>
                </div>

              </div>

            </div>

          )}

          <div className="grid gap-4 md:grid-cols-2">

            <div className="border border-green-500 rounded-lg p-5 bg-gray-900">

              <h3 className="text-xl font-bold text-green-400">
                🎯 Highlights Found
              </h3>

              <p className="text-4xl mt-3 font-bold">
                {
                  result.highlights_found
                }
              </p>

            </div>

            <div className="border border-blue-500 rounded-lg p-5 bg-gray-900">

              <h3 className="text-xl font-bold text-blue-400">
                🎬 Final Reel Preview
              </h3>

              <video
                controls
                className="mt-4 w-full rounded-lg"
              >
                <source
                  src={getVideoUrl()}
                  type="video/mp4"
                />
              </video>

              <button
                onClick={
                  downloadReel
                }
                className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-semibold"
              >
                ⬇ Open Reel
              </button>

              <button
                onClick={
                  downloadVerticalReel
                }
                className="mt-3 w-full bg-purple-600 hover:bg-purple-700 text-white p-3 rounded-lg font-semibold"
              >
                📱 Open Vertical Reel
              </button>

            </div>

          </div>

          <div className="mt-6 p-6 border border-purple-500 rounded-lg bg-gray-900">

            <h3 className="text-2xl font-bold text-purple-400">
              🔥 Viral Package
            </h3>

            <div className="mt-4">

              <p>
                <strong>
                  Title:
                </strong>
              </p>

              <p className="mt-2">
                {result.title}
              </p>

              <button
                onClick={() =>
                  copyToClipboard(
                    result.title || "",
                    "Title Copied"
                  )
                }
                className="mt-2 bg-yellow-600 px-4 py-2 rounded"
              >
                📋 Copy Title
              </button>

            </div>

            <div className="mt-6">

              <p>
                <strong>
                  Description:
                </strong>
              </p>

              <p className="mt-2">
                {
                  result.description
                }
              </p>

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
                onClick={
                  downloadResultsJson
                }
                className="mt-4 w-full bg-orange-600 hover:bg-orange-700 text-white p-3 rounded-lg font-semibold"
              >
                📄 Download Results JSON
              </button>      
            </div>

            <div className="mt-6">

              <p>
                <strong>
                  Hashtags:
                </strong>
              </p>

              <p className="mt-2">
                {result.hashtags?.join(
                  " "
                )}
              </p>

              <button
                onClick={() =>
                  copyToClipboard(
                    result.hashtags?.join(
                      " "
                    ) || "",
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

                  <h4 className="text-xl font-bold text-red-400">
                    📺 YouTube
                  </h4>

                  <textarea
                    readOnly
                    value={
                      result.social_exports?.youtube?.description || ""
                    }
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

                  <h4 className="text-xl font-bold text-pink-400">
                    📸 Instagram
                  </h4>

                  <textarea
                    readOnly
                    value={
                      result.social_exports?.instagram?.caption || ""
                    }
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

                  <h4 className="text-xl font-bold text-cyan-400">
                    🎵 TikTok
                  </h4>

                  <textarea
                    readOnly
                    value={
                      result.social_exports?.tiktok?.caption || ""
                    }
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

            <h3 className="text-2xl font-bold text-cyan-400">
              🖼 Best Thumbnail
            </h3>
            <button
              onClick={() =>
                window.open(
                  getThumbnailUrl(),
                  "_blank"
                )
              }
              className="mt-4 w-full bg-cyan-600 hover:bg-cyan-700 text-white p-3 rounded-lg font-semibold"
            >
              ⬇ Download Thumbnail
            </button>

            <img
              src={getThumbnailUrl()}
              alt="thumbnail"
              className="mt-4 rounded-lg max-h-[500px] object-cover mx-auto"
            />

          </div>

          {result.all_highlights &&
            result.all_highlights.length > 0 && (

              <div className="mt-8">

                <h3 className="text-3xl font-bold text-green-400 mb-6">
                  🎯 Top Highlights Gallery
                </h3>

                <div className="grid gap-6 md:grid-cols-2">

                  {result.all_highlights.map(
                    (
                      highlight: any,
                      index: number
                    ) => (

                      <div
                        key={index}
                        className="p-5 rounded-lg border border-green-500 bg-gray-900"
                      >

                        <h4 className="text-xl font-bold text-green-400 mb-3">
                          Highlight #{index + 1}
                        </h4>

                        <video
                          controls
                          className="w-full rounded-lg"
                        >
                          <source
                            src={getClipUrl(
                              highlight.clip_path
                            )}
                            type="video/mp4"
                          />
                        </video>

                        <div className="mt-4 space-y-2">

                          <p>
                            <strong>
                              Timestamp:
                            </strong>{" "}
                            {
                              highlight.timestamp
                            } sec
                          </p>

                          <p>
                            <strong>
                              Action:
                            </strong>{" "}
                            {
                              highlight.action
                            }
                          </p>

                          <p>
                            <strong>
                              Score:
                            </strong>{" "}
                            {(
                              highlight.score *
                              100
                            ).toFixed(2)}
                            %
                          </p>

                        </div>

                      </div>

                    )
                  )}

                </div>

              </div>

            )}

        </div>
      )}

    </main>
  );
}