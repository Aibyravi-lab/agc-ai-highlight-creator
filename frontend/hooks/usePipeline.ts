"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  uploadVideo,
  startPipeline,
  getJob,
  getHistory,
  getJobs,
  getJobStats,
  getProgress,
} from "../services/api";
import { track } from "../services/analytics";
import type {
  PipelineJob,
  JobStats,
  HistoryItem,
  ProgressData,
  ExtendedPipelineResult,
} from "../types/pipeline";

interface PipelineState {
  selectedFile: File | null;
  loading: boolean;
  progress: number;
  progressStatus: string;
  result: ExtendedPipelineResult | null;
  history: HistoryItem[];
  allJobs: PipelineJob[];
  jobStats: JobStats | null;
  error: string | null;
  currentJobId: string | null;
  successMessage: string | null;
  fileInputKey: number;
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>({
    selectedFile: null,
    loading: false,
    progress: 0,
    progressStatus: "",
    result: null,
    history: [],
    allJobs: [],
    jobStats: null,
    error: null,
    currentJobId: null,
    successMessage: null,
    fileInputKey: 0,
  });

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Ref that always holds the latest currentJobId without causing stale closures
  // in setInterval callbacks. Updated synchronously on every render.
  const currentJobIdRef = useRef<string | null>(null);
  currentJobIdRef.current = state.currentJobId;

  // Set selected file
  const setSelectedFile = useCallback((file: File | null) => {
    setState((prev) => ({ ...prev, selectedFile: file }));
  }, []);

  // Clear result
  const clearResult = useCallback(() => {
    setState((prev) => ({ ...prev, result: null }));
  }, []);

  // Stop polling and cleanup
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Dedicated effect for continuous job polling
  useEffect(() => {
    if (!state.currentJobId) {
      return;
    }

    const jobId = state.currentJobId;

    // Guard: clear any leftover interval before creating a new one
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await getJob(jobId);
        const job = response.data;

        if (job.status === "completed") {
          stopPolling();
          track("pipeline_completed");
          setState((prev) => {
            return { ...prev, result: job.result ?? null, loading: false, progress: 100, progressStatus: "Completed", currentJobId: null, selectedFile: null, successMessage: "Highlights generated successfully!", fileInputKey: prev.fileInputKey + 1 };
          });
          // Refresh all dashboard sections immediately after completion
          getHistory()
            .then((res) => setState((prev) => ({ ...prev, history: res.data || [] })))
            .catch((err) => console.error("History refresh failed:", err));
          getJobs()
            .then((res) => setState((prev) => ({ ...prev, allJobs: res.data || [] })))
            .catch((err) => console.error("Jobs refresh failed:", err));
          getJobStats()
            .then((res) => setState((prev) => ({ ...prev, jobStats: res.data || null })))
            .catch((err) => console.error("Stats refresh failed:", err));
        } else if (job.status === "failed") {
          stopPolling();
          setState((prev) => {
            return { ...prev, loading: false, error: job.error || "Processing failed", currentJobId: null };
          });
        } else {
          setState((prev) => {
            const nextProgressStatus = job.message || job.status;
            return { ...prev, progress: Math.max(prev.progress, job.progress ?? 0), progressStatus: nextProgressStatus };
          });
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);

    return () => {
      stopPolling();
    };
  }, [state.currentJobId, stopPolling]);

  // Generate highlights - main entry point
  const generateHighlights = useCallback(
    async (file: File) => {
      if (!file) {
        setState((prev) => ({
          ...prev,
          error: "Please select a video",
        }));
        return;
      }

      const SUPPORTED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
      const dotIndex = file.name.lastIndexOf(".");
      const ext = dotIndex === -1 ? "" : file.name.slice(dotIndex).toLowerCase();
      if (!SUPPORTED_EXTENSIONS.includes(ext)) {
        setState((prev) => ({
          ...prev,
          error: `Unsupported file type${ext ? ` "${ext}"` : ""}. Please upload a video file (MP4, MOV, AVI, MKV, WebM).`,
        }));
        return;
      }

      setState((prev) => {
        return { ...prev, loading: true, error: null, result: null, progress: 0, progressStatus: "Uploading...", successMessage: null };
      });

      try {
        track("upload_started");
        const uploadResponse = await uploadVideo(file);

        if (!uploadResponse.location) {
          throw new Error("Upload location missing");
        }

        track("upload_completed");
        setState((prev) => {
          return { ...prev, progressStatus: "Starting pipeline...", progress: 10 };
        });

        const startResponse = await startPipeline(uploadResponse.location);

        if (!startResponse.job_id) {
          throw new Error("Job ID missing from response");
        }

        track("pipeline_started");
        const jobId = startResponse.job_id;

        setState((prev) => {
          return { ...prev, currentJobId: jobId, progressStatus: "Processing...", progress: 20 };
        });
      } catch (err) {
        const isTimeout = (err as { name?: string } | null)?.name === "AbortError";
        const errorMessage = isTimeout
          ? "Upload timed out after 60 seconds. Please try again."
          : err instanceof Error
          ? err.message
          : "Upload failed. Please check your internet connection and try again.";

        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
          progress: 0,
          progressStatus: "",
        }));
      }
    },
    []
  );

  // Load history
  const loadHistory = useCallback(async () => {
    try {
      const response = await getHistory();
      setState((prev) => ({
        ...prev,
        history: response.data || [],
      }));
    } catch (err) {
      console.error("History load failed:", err);
    }
  }, []);

  // Load all jobs
  const loadAllJobs = useCallback(async () => {
    try {
      const response = await getJobs();
      setState((prev) => ({
        ...prev,
        allJobs: response.data || [],
      }));
    } catch (err) {
      console.error("Jobs load failed:", err);
    }
  }, []);

  // Load job stats
  const loadJobStats = useCallback(async () => {
    try {
      const response = await getJobStats();
      setState((prev) => ({
        ...prev,
        jobStats: response.data || null,
      }));
    } catch (err) {
      console.error("Job stats load failed:", err);
    }
  }, []);

  // Load progress - only when no active job.
  // Uses ref so this callback is stable and never closes over stale state.
  const loadProgress = useCallback(async () => {
    if (currentJobIdRef.current) {
      return;
    }
    try {
      const response = await getProgress();
      setState((prev) => {
        const nextProgressStatus = response.data?.status || "";
        return { ...prev, progress: Math.max(prev.progress, response.data?.progress ?? 0), progressStatus: nextProgressStatus };
      });
    } catch (err) {
      console.error("Progress load failed:", err);
    }
  }, []); // stable — reads currentJobIdRef, not state

  // Initialize once on mount. Does NOT depend on currentJobId:
  // the interval callback reads currentJobIdRef.current for a fresh value
  // without needing the effect to re-run on every job state change.
  useEffect(() => {
    loadHistory();
    loadJobStats();
    loadAllJobs();

    const interval = setInterval(() => {
      if (!currentJobIdRef.current) {
        loadProgress();
      }
      loadJobStats();
      loadAllJobs();
      loadHistory();
    }, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [loadHistory, loadJobStats, loadAllJobs, loadProgress]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  const clearSuccessMessage = useCallback(() => {
    setState((prev) => ({ ...prev, successMessage: null }));
  }, []);

  return {
    // State
    selectedFile: state.selectedFile,
    loading: state.loading,
    progress: state.progress,
    progressStatus: state.progressStatus,
    result: state.result,
    history: state.history,
    allJobs: state.allJobs,
    jobStats: state.jobStats,
    error: state.error,
    currentJobId: state.currentJobId,
    successMessage: state.successMessage,
    fileInputKey: state.fileInputKey,

    // Actions
    setSelectedFile,
    generateHighlights,
    loadHistory,
    loadAllJobs,
    loadJobStats,
    loadProgress,
    clearResult,
    clearError,
    clearSuccessMessage,
    stopPolling,
  };
}
