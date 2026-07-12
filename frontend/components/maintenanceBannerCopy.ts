// AGC-084: single source of truth for the CTO-approved maintenance
// banner copy. Kept in its own JSX-free module so the exact text is
// directly testable with node:test (this project has no
// jsdom/React-testing-library to render MaintenanceBanner.tsx itself).
export const MAINTENANCE_BANNER_MESSAGE =
  "Vedzovi is upgrading.\n" +
  "AI processing is temporarily paused for a quick update.\n" +
  "Your existing projects are safe.\n" +
  "Estimated time: 5–10 minutes.";
