import type { MissionControlSummary } from "../types/missionControl";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("agc_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getMissionControlSummary(): Promise<MissionControlSummary> {
  const response = await fetch(`${API_BASE}/admin/mission-control/summary`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });

  if (!response.ok) {
    let message = "Unable to load Mission Control data.";
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
