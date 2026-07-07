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
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      cache: "no-store",
      ...options,
    });
  } catch (err) {
    // Preserve AbortError identity so callers (e.g. an upload timeout) can
    // distinguish "request aborted" from a genuine network failure.
    if ((err as { name?: string } | null)?.name === "AbortError") {
      throw err;
    }
    throw new Error("Unable to reach the server. Please try again.");
  }

  if (!response.ok) {
    let message = "Something went wrong. Please try again.";

    try {
      const error = await response.json();

      message =
        (typeof error.detail === "string" ? error.detail : error.detail?.message) ||
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

const UPLOAD_TIMEOUT_MS = 60000;

export async function uploadVideo(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  try {
    return await authedRequest("/upload/", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
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

/**
 * File access — every stored file (reel, thumbnail, clip, result JSON) is
 * served exclusively through the authenticated /files/ endpoint, which
 * verifies ownership before returning the bytes. There is no unauthenticated
 * static file access.
 */

function filenameFromPath(path: string): string {
  return decodeURIComponent(path.split(/[\\/]/).pop() || "download");
}

async function fetchAuthedBlob(relativePath: string): Promise<Blob> {
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
  return response.blob();
}

async function authedBlobDownload(
  relativePath: string,
  filename: string
): Promise<void> {
  const blob = await fetchAuthedBlob(relativePath);
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

/**
 * Fetches a stored file via the authenticated /files/ endpoint and returns a
 * local object URL suitable for <img>/<video> src attributes. Callers own
 * the returned URL and must revoke it (URL.revokeObjectURL) once done.
 */
export async function fetchAuthedMediaUrl(
  relativePath: string
): Promise<string> {
  const blob = await fetchAuthedBlob(relativePath);
  return URL.createObjectURL(blob);
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

export async function submitFeedback(
  body: import("../types/pipeline").SubmitFeedbackRequest
) {
  return authedRequest("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }) as Promise<{
    success: boolean;
    data: import("../types/pipeline").FeedbackItem;
  }>;
}

export async function getSubscription() {
  return authedRequest(
    "/subscription/me"
  ) as Promise<import("../types/subscription").SubscriptionInfo>;
}

export async function upgradeToPro() {
  return authedRequest("/subscription/mock-upgrade", {
    method: "POST",
  }) as Promise<import("../types/subscription").SubscriptionInfo>;
}

export async function createPaymentOrder(plan: string) {
  return authedRequest("/payments/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  }) as Promise<import("../types/payment").RazorpayOrder>;
}

export async function verifyPayment(
  payment: import("../types/payment").RazorpayPaymentSuccess
) {
  return authedRequest("/payments/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payment),
  }) as Promise<{ success: boolean; plan: string; status: string }>;
}

export async function getFeedback() {
  return authedRequest("/feedback") as Promise<{
    success: boolean;
    count: number;
    data: import("../types/pipeline").FeedbackItem[];
  }>;
}

export async function deleteFeedback(id: number) {
  return authedRequest(`/feedback/${id}`, { method: "DELETE" }) as Promise<{
    success: boolean;
    message: string;
  }>;
}