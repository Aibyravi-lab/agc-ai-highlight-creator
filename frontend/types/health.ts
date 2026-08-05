export type CheckStatusValue = "healthy" | "warning" | "critical" | "unknown";

export type ProductionStatus = "healthy" | "degraded" | "critical";

export interface HealthCheckEntry {
  status: CheckStatusValue;
  message: string;
  evidence: Record<string, unknown>;
}

export interface OpenAlert {
  id: number;
  check_id: string;
  severity: "warning" | "critical";
  root_cause: string;
  evidence: Record<string, unknown>;
  suggested_fix: string;
  time: string;
  resolved_at: string | null;
}

export interface HealthSummary {
  score: number;
  status: ProductionStatus;
  generated_at: string;
  checks: Record<string, HealthCheckEntry>;
  open_alerts: OpenAlert[];
}

export interface HealthSnapshot {
  created_at: string;
  score: number;
  status: string;
}

export type TrendDirection = "improving" | "declining" | "stable" | "unknown";

export interface HealthTrend {
  avg_score: number | null;
  min_score: number | null;
  max_score: number | null;
  current_score: number | null;
  direction: TrendDirection;
}

export type HealthHistoryRange = "today" | "yesterday" | "7d" | "30d";

export interface HealthHistory {
  range: HealthHistoryRange;
  snapshots: HealthSnapshot[];
  trend: HealthTrend;
}

export interface AlertsResponse {
  alerts: OpenAlert[];
}
