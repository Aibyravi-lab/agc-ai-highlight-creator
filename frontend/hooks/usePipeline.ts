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
  });

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
    // Only poll if we have an active job
    if (!state.currentJobId) {
      return;
    }

    const jobId = state.currentJobId; // Capture jobId as non-null string

    // Start polling loop every 2 seconds
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await getJob(jobId);
        const job = response.data;

        // Update progress (never moves backwards)
        setState((prev) => ({
          ...prev,
          progress: Math.max(prev.progress, job.progress || 0),
          progressStatus: job.status,
        }));

        // Stop polling when job completes
        if (job.status === "completed") {
          stopPolling();
          setState((prev) => ({
            ...prev,
            result: job.result,
            loading: false,
            progress: 100,
            progressStatus: "Completed",
            currentJobId: null,
          }));
          // Refresh history after completion
          try {
            const historyResponse = await getHistory();
            setState((prev) => ({
              ...prev,
              history: historyResponse.data || [],
            }));
          } catch (err) {
            console.error("History load failed:", err);
          }
        } else if (job.status === "failed") {
          // Stop polling when job fails
          stopPolling();
          setState((prev) => ({
            ...prev,
            loading: false,
            error: job.error || "Processing failed",
            currentJobId: null,
          }));
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000); // Poll every 2 seconds

    // Cleanup: stop polling when effect unmounts or job ID changes
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

      setState((prev) => ({
        ...prev,
        loading: true,
        error: null,
        result: null,
        progress: 0,
        progressStatus: "Uploading...",
      }));

      try {
        // Step 1: Upload video
        const uploadResponse = await uploadVideo(file);

        if (!uploadResponse.location) {
          throw new Error("Upload location missing");
        }

        setState((prev) => ({
          ...prev,
          progressStatus: "Starting pipeline...",
          progress: 10,
        }));

        // Step 2: Start pipeline
        const startResponse = await startPipeline(uploadResponse.location);

        if (!startResponse.job_id) {
          throw new Error("Job ID missing from response");
        }

        const jobId = startResponse.job_id;

        // Step 3: Store job ID to trigger polling effect
        setState((prev) => ({
          ...prev,
          currentJobId: jobId,
          progressStatus: "Processing...",
          progress: 20,
        }));
        // Polling effect automatically starts when currentJobId is set
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Processing failed";
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
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

  // Load progress - only when no active job
  const loadProgress = useCallback(async () => {
    // Skip if there's an active job being polled
    if (state.currentJobId) {
      return;
    }

    try {
      const response = await getProgress();
      setState((prev) => ({
        ...prev,
        progress: Math.max(prev.progress, response.data?.progress || 0),
        progressStatus: response.data?.current_step || "",
      }));
    } catch (err) {
      console.error("Progress load failed:", err);
    }
  }, [state.currentJobId]);

  // Initialize - load initial data and refresh dashboard
  useEffect(() => {
    loadHistory();
    loadJobStats();
    loadAllJobs();

    // Refresh dashboard every 5 seconds (don't interfere with job polling)
    const interval = setInterval(() => {
      // Only call loadProgress when there's no active job
      if (!state.currentJobId) {
        loadProgress();
      }
      loadJobStats();
      loadAllJobs();
    }, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [loadHistory, loadJobStats, loadAllJobs, loadProgress, state.currentJobId]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
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

    // Actions
    setSelectedFile,
    generateHighlights,
    loadHistory,
    loadAllJobs,
    loadJobStats,
    loadProgress,
    clearResult,
    clearError,
    stopPolling,
  };
}
