export interface ProductionHealth {
  status: string;
  database: string;
  ffmpeg: string;
  uptime_seconds: number;
  maintenance_mode: boolean;
  environment: string;
}

export interface LiveMetrics {
  // GROW-005.2: total_users/verified_users/users_with_jobs/
  // users_with_completed_jobs/repeat_users/active_pro_users/
  // processed_payments/distinct_feedback_users reflect EXTERNAL users only.
  total_users: number;
  internal_users: number;
  verified_users: number;
  users_with_jobs: number;
  users_with_completed_jobs: number;
  repeat_users: number;
  // total_jobs/completed_jobs/failed_jobs are unfiltered operational totals
  // (all jobs, incl. internal/test) — used for infra health, not traction.
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  // external_* are the growth-facing counterparts for UI that presents job
  // activity as user traction.
  external_total_jobs: number;
  external_completed_jobs: number;
  external_failed_jobs: number;
  internal_jobs: number;
  // Jobs with no resolvable owner (user_id IS NULL) — counted operationally
  // above, never as external or internal growth traction.
  unattributed_jobs: number;
  active_pro_users: number;
  processed_payments: number;
  distinct_feedback_users: number;
}

export interface Revenue {
  // REVENUE-005: derived from live_metrics.processed_payments /
  // active_pro_users × the current PLAN_PRICING price — not a stored
  // historical ledger. historical_pricing_supported is false because
  // payments do not persist the amount actually charged, so this is only
  // accurate as long as the plan price has never changed.
  gross_processed_revenue_paise: number;
  estimated_mrr_paise: number;
  currency: string;
  price_source: string;
  historical_pricing_supported: boolean;
}

export interface CreditBreakdown {
  exhausted: number;
  low: number;
  healthy: number;
}

export interface JobsPerUserBuckets {
  "1": number;
  "2-3": number;
  "4-5": number;
  "6+": number;
}

export interface Distribution {
  credit_breakdown: CreditBreakdown;
  jobs_per_user: JobsPerUserBuckets;
}

export interface CapabilityEntry {
  name: string;
  evidence: string;
}

export interface CapabilityCategory {
  category: string;
  capabilities: CapabilityEntry[];
}

export interface Blocker {
  id: string;
  severity: "warning" | "info";
  message: string;
}

export interface ReleaseInfo {
  app_version: string;
  git_commit: string;
  git_tag: string;
  ci: {
    workflow: string;
    note: string;
  };
}

export interface DailyActivity {
  date: string;
  total: number;
  completed: number;
  failed: number;
}

export interface SocialIntegration {
  platform: string;
  status: "not_connected" | "connected";
}

export interface FeedbackRatingDistribution {
  great: number;
  good: number;
  okay: number;
  bad: number;
}

export interface FeedbackSummary {
  total_responses: number;
  positive_rate: number | null;
  rating_distribution: FeedbackRatingDistribution;
  top_improvement_area: string | null;
}

export interface Segmentation {
  external_users: number;
  internal_users: number;
  external_jobs: number;
  internal_jobs: number;
  unattributed_jobs: number;
  note: string;
}

export interface MissionControlSummary {
  production_health: ProductionHealth;
  live_metrics: LiveMetrics;
  revenue: Revenue;
  distribution: Distribution;
  capability_registry: CapabilityCategory[];
  blockers: Blocker[];
  release: ReleaseInfo;
  weekly_activity: DailyActivity[];
  social_integrations: SocialIntegration[];
  feedback_summary: FeedbackSummary;
  segmentation: Segmentation;
}
