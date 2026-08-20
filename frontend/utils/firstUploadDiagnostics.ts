// VED-GROWTH-001 Slice 2: pure fire-once decisions for the first-upload
// diagnostic events, extracted out of the components so this JSX-free
// module is directly testable with node:test — same pattern as
// utils/uploadPanelState.ts (this project has no jsdom/React-testing-library
// to render the components themselves).

export interface JobCounts {
  queued: number;
  running: number;
  completed: number;
  failed: number;
}

// null jobStats means the job count hasn't loaded yet — treated as "not
// zero" so callers never fire while still waiting to find out.
export function hasZeroJobs(jobStats: JobCounts | null): boolean {
  if (jobStats === null) return false;
  return jobStats.queued + jobStats.running + jobStats.completed + jobStats.failed === 0;
}

export interface DashboardFirstVisitEmptyAvailability {
  jobStats: JobCounts | null;
  alreadyTracked: boolean;
}

export function shouldTrackDashboardFirstVisitEmpty({
  jobStats,
  alreadyTracked,
}: DashboardFirstVisitEmptyAvailability): boolean {
  return !alreadyTracked && hasZeroJobs(jobStats);
}

export interface UploadUiSeenAvailability {
  zeroJobs: boolean;
  maintenanceMode: boolean;
  subscriptionLoading: boolean;
  outOfCredits: boolean;
  alreadyTracked: boolean;
}

export function shouldTrackUploadUiSeen({
  zeroJobs,
  maintenanceMode,
  subscriptionLoading,
  outOfCredits,
  alreadyTracked,
}: UploadUiSeenAvailability): boolean {
  return (
    !alreadyTracked &&
    zeroJobs &&
    !maintenanceMode &&
    !subscriptionLoading &&
    !outOfCredits
  );
}
