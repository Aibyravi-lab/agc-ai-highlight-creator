"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { usePipeline } from "../../hooks/usePipeline";
import { UploadPanel } from "../../components/UploadPanel";
import { ProgressPanel } from "../../components/ProgressPanel";
import { StatsPanel } from "../../components/StatsPanel";
import { HistoryPanel } from "../../components/HistoryPanel";
import { ProjectsPanel } from "../../components/ProjectsPanel";
import { DownloadPanel } from "../../components/DownloadPanel";
import { ResultPanel } from "../../components/ResultPanel";
import { FeedbackCard } from "../../components/FeedbackCard";
import { useAuth } from "../../context/AuthContext";
import { track, reset } from "../../services/analytics";
import type { AuthUser } from "../../types/auth";
import type { ExtendedPipelineResult, PipelineJob } from "../../types/pipeline";

export default function Home() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#08090d] flex items-center justify-center">
        <div className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <DashboardContent user={user} logout={logout} />;
}

function DashboardContent({
  user,
  logout,
}: {
  user: AuthUser;
  logout: () => void;
}) {
  const router = useRouter();

  const [feedbackDismissed, setFeedbackDismissed] = useState(false);
  const prevResultRef = useRef<ExtendedPipelineResult | null>(null);

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
    currentJobId,
    successMessage,
    fileInputKey,
    setSelectedFile,
    generateHighlights,
    clearError,
    clearSuccessMessage,
  } = usePipeline();

  const handleLogout = () => {
    track("User Logged Out");
    reset();
    logout();
    router.replace("/login");
  };

  const handleGenerateHighlights = async () => {
    if (selectedFile) {
      await generateHighlights(selectedFile);
    }
  };

  useEffect(() => {
    if (result !== null && result !== prevResultRef.current) {
      setFeedbackDismissed(false);
      track("Feedback Opened");
    }
    prevResultRef.current = result;
  }, [result]);

  const currentJob: PipelineJob | null = currentJobId
    ? (allJobs.find((j) => j.job_id === currentJobId) ?? null)
    : null;

  return (
    <main className="min-h-screen bg-[#08090d] text-white">
      <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">

        {/* Header */}
        <div className="pb-2 border-b border-[#1a1d2e]">
          <div className="flex items-center justify-between">
            <div className="flex items-baseline gap-3">
              <h1 className="text-2xl font-bold tracking-tight">AGC</h1>
              <span className="text-gray-500 text-sm">AI Gaming Highlight Creator</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-500 text-sm hidden sm:block">{user.name}</span>
              <button
                onClick={handleLogout}
                aria-label="Sign out"
                className="text-sm text-gray-400 hover:text-white border border-[#1a1d2e] hover:border-[#2a2d3e] px-3 py-1.5 rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-400"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>

        {/* Upload */}
        <section>
          <UploadPanel
            selectedFile={selectedFile}
            loading={loading}
            onSelectFile={setSelectedFile}
            onGenerateHighlights={handleGenerateHighlights}
            fileInputKey={fileInputKey}
          />
        </section>

        {/* Current Job */}
        <section>
          <ProgressPanel
            loading={loading}
            progress={progress}
            progressStatus={progressStatus}
            error={error}
            onClearError={clearError}
            currentJobId={currentJobId}
            currentJob={currentJob}
            successMessage={successMessage}
            onClearSuccessMessage={clearSuccessMessage}
          />
        </section>

        {/* System Statistics + Recent Jobs */}
        <section>
          <StatsPanel jobStats={jobStats} allJobs={allJobs} />
        </section>

        {/* History */}
        <section>
          <HistoryPanel history={history} />
        </section>

        {/* My Projects */}
        <section>
          <ProjectsPanel />
        </section>

        {/* Results */}
        {result && (
          <section className="space-y-6">
            <DownloadPanel result={result} />
            <ResultPanel result={result} />
            {!feedbackDismissed && (
              <FeedbackCard onDismiss={() => setFeedbackDismissed(true)} />
            )}
          </section>
        )}

      </div>
    </main>
  );
}
