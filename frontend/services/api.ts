const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(
  endpoint: string,
  options: RequestInit = {}
) {
  const response = await fetch(`${API_BASE}${endpoint}`, options);

  if (!response.ok) {
    let message = "Something went wrong.";

    try {
      const error = await response.json();

      message =
        error.detail ||
        error.message ||
        JSON.stringify(error);
    } catch {
      message = await response.text();
    }

    throw new Error(message);
  }

  return response.json();
}

/**
 * Data transformation functions to map backend responses to frontend interfaces
 */

type BackendJobStatus = "pending" | "processing" | "completed" | "failed";
type FrontendJobStatus = "queued" | "running" | "completed" | "failed";

function mapJobStatus(backendStatus: string): FrontendJobStatus {
  const statusMap: Record<string, FrontendJobStatus> = {
    pending: "queued",
    processing: "running",
    completed: "completed",
    failed: "failed",
  };
  return statusMap[backendStatus] || ("queued" as FrontendJobStatus);
}

function mapHighlight(backendHighlight: any) {
  return {
    timestamp: backendHighlight.timestamp,
    duration: backendHighlight.duration,
    score: backendHighlight.score,
    action: backendHighlight.action,
    label: backendHighlight.category,
    clip_path: backendHighlight.clip_path,
  };
}

function mapResult(backendResult: any) {
  if (!backendResult) return null;

  return {
    title: backendResult.title,
    description: backendResult.description,
    hashtags: backendResult.hashtags,
    final_reel: backendResult.final_reel,
    vertical_reel: backendResult.vertical_reel,
    thumbnail: backendResult.thumbnail,
    result_json: backendResult.result_json,
    highlights_found: backendResult.highlights_found || 0,
    stats: backendResult.stats,
    all_highlights: backendResult.all_highlights?.map(mapHighlight) || [],
  };
}

function mapJob(backendJob: any) {
  return {
    job_id: backendJob.job_id,
    status: mapJobStatus(backendJob.status),
    progress: backendJob.progress,
    created_at: backendJob.created_at,
    error: backendJob.error || null,
    result: mapResult(backendJob.result),
  };
}

export async function uploadVideo(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return request("/upload/", {
    method: "POST",
    body: formData,
  });
}

export async function startPipeline(videoPath: string) {
  return request(
    `/pipeline/start?video_path=${encodeURIComponent(videoPath)}`,
    {
      method: "POST",
    }
  );
}

export async function getJob(jobId: string) {
  const response = await request(`/pipeline/job/${jobId}`);
  return {
    ...response,
    data: mapJob(response.data),
  };
}

export async function getJobs() {
  const response = await request("/pipeline/jobs");
  return {
    ...response,
    data: response.data.map(mapJob),
  };
}

export async function getJobStats() {
  const response = await request("/pipeline/jobs/stats");
  const stats = response.data;
  return {
    success: response.success,
    data: {
      queued: stats.pending_jobs || 0,
      running: stats.processing_jobs || 0,
      completed: stats.completed_jobs || 0,
      failed: stats.failed_jobs || 0,
    },
  };
}

export async function getProgress() {
  return request("/pipeline/progress");
}

export async function getHistory() {
  const response = await request("/history/");
  return {
    success: response.success,
    data: response.data.map((item: any) => ({
      video_name: item.video_name,
      date: item.date,
      reel_path: item.reel_path,
      highlights_count: item.highlights_count,
    })),
  };
}

/**
 * Helper functions for URL construction
 */

function normalizePathToUrl(path: string): string {
  return path.replaceAll("\\", "/");
}

export function getReelUrl(reelPath: string | undefined): string {
  if (!reelPath) return "";
  return `${API_BASE}/${normalizePathToUrl(reelPath)}`;
}

export function getVerticalReelUrl(verticalPath: string | undefined): string {
  if (!verticalPath) return "";
  return `${API_BASE}/${normalizePathToUrl(verticalPath)}`;
}

export function getThumbnailUrl(thumbnailPath: string | undefined): string {
  if (!thumbnailPath) return "";
  return `${API_BASE}/${normalizePathToUrl(thumbnailPath)}`;
}

export function getClipUrl(clipPath: string | undefined): string {
  if (!clipPath) return "";
  return `${API_BASE}/${normalizePathToUrl(clipPath)}`;
}

export function getResultJsonUrl(resultJsonPath: string | undefined): string {
  if (!resultJsonPath) return "";
  return `${API_BASE}/${normalizePathToUrl(resultJsonPath)}`;
}

/**
 * Download functions that handle window.open() internally
 */

export function downloadReel(reelPath: string | undefined) {
  const url = getReelUrl(reelPath);
  if (!url) {
    alert("No reel available");
    return;
  }
  window.open(url, "_blank");
}

export function downloadVerticalReel(verticalPath: string | undefined) {
  const url = getVerticalReelUrl(verticalPath);
  if (!url) {
    alert("No vertical reel available");
    return;
  }
  window.open(url, "_blank");
}

export function downloadThumbnail(thumbnailPath: string | undefined) {
  const url = getThumbnailUrl(thumbnailPath);
  if (!url) {
    alert("No thumbnail available");
    return;
  }
  window.open(url, "_blank");
}

export function downloadResultJson(resultJsonPath: string | undefined) {
  const url = getResultJsonUrl(resultJsonPath);
  if (!url) {
    alert("Results JSON not found");
    return;
  }
  window.open(url, "_blank");
}

export function downloadClip(clipPath: string | undefined) {
  const url = getClipUrl(clipPath);
  if (!url) {
    alert("No clip available");
    return;
  }
  window.open(url, "_blank");
}