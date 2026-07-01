const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("agc_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(
  endpoint: string,
  options: RequestInit = {}
) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    cache: "no-store",
    ...options,
  });

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

function authedRequest(endpoint: string, options: RequestInit = {}) {
  return request(endpoint, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
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
    message: backendJob.message || "",
    created_at: backendJob.created_at,
    error: backendJob.error || null,
    result: mapResult(backendJob.result),
  };
}

export async function uploadVideo(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return authedRequest("/upload/", {
    method: "POST",
    body: formData,
  });
}

export async function startPipeline(videoPath: string) {
  return authedRequest(
    `/pipeline/start?video_path=${encodeURIComponent(videoPath)}`,
    {
      method: "POST",
    }
  );
}

export async function getJob(jobId: string) {
  const response = await authedRequest(`/pipeline/job/${jobId}`);
  return {
    ...response,
    data: mapJob(response.data),
  };
}

export async function getJobs() {
  const response = await authedRequest("/pipeline/jobs");
  return {
    ...response,
    data: response.data.map(mapJob),
  };
}

export async function getJobStats() {
  const response = await authedRequest("/pipeline/jobs/stats");
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
  return authedRequest("/pipeline/progress");
}

export async function getHistory() {
  const response = await authedRequest("/history/");
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
 * Download functions — fetch via the authenticated /files/ endpoint so the
 * server can verify ownership before serving.  Signatures are unchanged so
 * callers need no updates.
 */

function filenameFromPath(path: string): string {
  return decodeURIComponent(path.split(/[\\/]/).pop() || "download");
}

async function authedBlobDownload(
  relativePath: string,
  filename: string
): Promise<void> {
  const normalized = normalizePathToUrl(relativePath);
  const response = await fetch(`${API_BASE}/files/${normalized}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(
      response.status === 403 ? "Access denied" : "Download failed"
    );
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

export async function downloadReel(reelPath: string | undefined): Promise<void> {
  if (!reelPath) return;
  await authedBlobDownload(reelPath, filenameFromPath(reelPath));
}

export async function downloadVerticalReel(verticalPath: string | undefined): Promise<void> {
  if (!verticalPath) return;
  await authedBlobDownload(verticalPath, filenameFromPath(verticalPath));
}

export async function downloadThumbnail(thumbnailPath: string | undefined): Promise<void> {
  if (!thumbnailPath) return;
  await authedBlobDownload(thumbnailPath, filenameFromPath(thumbnailPath));
}

export async function downloadResultJson(resultJsonPath: string | undefined): Promise<void> {
  if (!resultJsonPath) return;
  await authedBlobDownload(resultJsonPath, filenameFromPath(resultJsonPath));
}

export async function downloadClip(clipPath: string | undefined): Promise<void> {
  if (!clipPath) return;
  await authedBlobDownload(clipPath, filenameFromPath(clipPath));
}

export async function getProjects() {
  const response = await authedRequest("/projects");
  return {
    success: response.success as boolean,
    count: response.count as number,
    data: response.data as import("../types/pipeline").ProjectItem[],
  };
}

export async function deleteProject(id: number) {
  return authedRequest(`/projects/${id}`, { method: "DELETE" }) as Promise<{
    success: boolean;
    message: string;
  }>;
}