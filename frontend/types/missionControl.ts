export interface ProductionHealth {
  status: string;
  database: string;
  ffmpeg: string;
  uptime_seconds: number;
  maintenance_mode: boolean;
  environment: string;
}

export interface LiveMetrics {
  total_users: number;
  verified_users: number;
  users_with_jobs: number;
  users_with_completed_jobs: number;
  repeat_users: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  active_pro_users: number;
  processed_payments: number;
  distinct_feedback_users: number;
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

export interface MissionControlSummary {
  production_health: ProductionHealth;
  live_metrics: LiveMetrics;
  distribution: Distribution;
  capability_registry: CapabilityCategory[];
  blockers: Blocker[];
  release: ReleaseInfo;
  weekly_activity: DailyActivity[];
  social_integrations: SocialIntegration[];
}
