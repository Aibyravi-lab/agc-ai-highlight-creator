"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { usePipeline } from "../../hooks/usePipeline";
import { useSubscription } from "../../hooks/useSubscription";
import { useMaintenanceStatus } from "../../hooks/useMaintenanceStatus";
import { UploadPanel } from "../../components/UploadPanel";
import { MaintenanceBanner } from "../../components/MaintenanceBanner";
import { ProgressPanel } from "../../components/ProgressPanel";
import { StatsPanel } from "../../components/StatsPanel";
import { HistoryPanel } from "../../components/HistoryPanel";
import { ProjectsPanel } from "../../components/ProjectsPanel";
import { DownloadPanel } from "../../components/DownloadPanel";
import { ResultPanel } from "../../components/ResultPanel";
import { FeedbackCard } from "../../components/FeedbackCard";
import { useAuth } from "../../context/AuthContext";
import { track, reset } from "../../services/analytics";
import { downloadReel, downloadVerticalReel, downloadThumbnail } from "../../services/api";
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
      <div className="min-h-screen bg-[#08090d] flex flex-col items-center justify-center gap-3">
        <div className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
        <p className="text-gray-500 text-sm">Loading your dashboard...</p>
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
    historyLoading,
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
    clearResult,
  } = usePipeline();

  const { subscription, loading: subscriptionLoading } = useSubscription();
  const isPro = subscription?.plan === "PRO";
  const maintenanceMode = useMaintenanceStatus();

  useEffect(() => {
    track("Dashboard Viewed");
  }, []);

  const handleLogout = () => {
    track("logout");
    track("Logout");
    reset();
    logout();
    router.replace("/login");
  };

  const handleGenerateHighlights = async () => {
    if (selectedFile) {
      await generateHighlights(selectedFile);
    }
  };

  const handleDownloadPrimary = () => {
    if (result?.final_reel) {
      track("Download Reel");
      downloadReel(result.final_reel);
    } else if (result?.vertical_reel) {
      track("Download Reel");
      downloadVerticalReel(result.vertical_reel);
    } else if (result?.thumbnail) {
      track("Download Thumbnail");
      downloadThumbnail(result.thumbnail);
    }
  };

  const handleCreateAnother = () => {
    clearResult();
    clearSuccessMessage();
    document.getElementById("upload-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const hasPrimaryDownload = Boolean(
    result?.final_reel || result?.vertical_reel || result?.thumbnail
  );

  useEffect(() => {
    if (result !== null && result !== prevResultRef.current) {
      setFeedbackDismissed(false);
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
              <h1 className="text-2xl font-bold tracking-tight">Vedzovi</h1>
              <span className="text-gray-500 text-sm">AI Video Intelligence</span>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/pricing"
                className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-400 focus-visible:rounded"
              >
                Pricing
              </Link>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  subscriptionLoading
                    ? "bg-[#1a1d2e] text-gray-600 animate-pulse"
                    : isPro
                    ? "bg-purple-500/15 text-purple-400"
                    : "bg-[#1a1d2e] text-gray-400"
                }`}
              >
                {subscriptionLoading ? "···" : isPro ? "PRO" : "FREE"}
              </span>
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

        {maintenanceMode && <MaintenanceBanner />}

        {/* Upload */}
        <section id="upload-panel">
          <UploadPanel
            selectedFile={selectedFile}
            loading={loading}
            progressStatus={progressStatus}
            onSelectFile={setSelectedFile}
            onGenerateHighlights={handleGenerateHighlights}
            fileInputKey={fileInputKey}
            creditsRemaining={user.credits_remaining}
            isPro={isPro}
            subscriptionLoading={subscriptionLoading}
            maintenanceMode={maintenanceMode}
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
            onDownload={hasPrimaryDownload ? handleDownloadPrimary : undefined}
            onCreateAnother={handleCreateAnother}
          />
        </section>

        {/* System Statistics + Recent Jobs */}
        <section>
          <StatsPanel
            jobStats={jobStats}
            allJobs={allJobs}
            creditsRemaining={user.credits_remaining}
            isPro={isPro}
            subscriptionLoading={subscriptionLoading}
          />
        </section>

        {/* History */}
        <section>
          <HistoryPanel history={history} historyLoading={historyLoading} />
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
