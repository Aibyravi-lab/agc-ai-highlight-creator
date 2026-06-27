"use client";

import { usePipeline } from "../hooks/usePipeline";
import { UploadPanel } from "../components/UploadPanel";
import { ProgressPanel } from "../components/ProgressPanel";
import { StatsPanel } from "../components/StatsPanel";
import { HistoryPanel } from "../components/HistoryPanel";
import { DownloadPanel } from "../components/DownloadPanel";
import { ResultPanel } from "../components/ResultPanel";


export default function Home() {
  const {
    selectedFile,
    loading,
    progress,
    progressStatus,
    result,
    history,
    allJobs,
    jobStats,
    error,
    setSelectedFile,
    generateHighlights,
    clearError,
  } = usePipeline();

  const handleGenerateHighlights = async () => {
    if (selectedFile) {
      await generateHighlights(selectedFile);
    }
  };

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center p-10">
      <h1 className="text-6xl font-bold">🎮 AGC</h1>
      <p className="mt-4 text-3xl">AI Gaming Highlight Creator</p>

      <UploadPanel
        selectedFile={selectedFile}
        loading={loading}
        onSelectFile={setSelectedFile}
        onGenerateHighlights={handleGenerateHighlights}
      />

      <ProgressPanel
        loading={loading}
        progress={progress}
        progressStatus={progressStatus}
        error={error}
        onClearError={clearError}
      />

      <StatsPanel jobStats={jobStats} allJobs={allJobs} />

      <HistoryPanel history={history} />

      <DownloadPanel result={result} />

      <ResultPanel result={result} />
    </main>
  );
}
