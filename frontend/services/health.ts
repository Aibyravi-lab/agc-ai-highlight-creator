import type { AlertsResponse, HealthHistory, HealthHistoryRange, HealthSummary } from "../types/health";

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim() || "";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("agc_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });

  if (!response.ok) {
    let message = "Unable to load health data.";
    try {
      const error = await response.json();
      message =
        (typeof error.detail === "string" ? error.detail : error.detail?.message) ||
        error.message ||
        message;
    } catch {
      // Keep the generic message if the error body isn't JSON.
    }
    throw new Error(message);
  }

  return response.json();
}

export function getHealthSummary(): Promise<HealthSummary> {
  return getJson<HealthSummary>("/admin/health/summary");
}

export function getHealthHistory(range: HealthHistoryRange): Promise<HealthHistory> {
  return getJson<HealthHistory>(`/admin/health/history?range=${range}`);
}

export function getHealthAlerts(resolved?: boolean): Promise<AlertsResponse> {
  const query = resolved === undefined ? "" : `?resolved=${resolved}`;
  return getJson<AlertsResponse>(`/admin/health/alerts${query}`);
}
