import posthog from "posthog-js";

type AnalyticsEvent =
  | "Landing Viewed"
  | "Login Clicked"
  | "Register Clicked"
  | "Learn More Clicked"
  | "User Registered"
  | "User Logged In"
  | "Upload Started"
  | "Upload Completed"
  | "Pipeline Started"
  | "Pipeline Completed"
  | "Project Downloaded"
  | "Project Deleted"
  | "User Logged Out"
  | "Feedback Opened"
  | "Feedback Submitted"
  | "Feedback Skipped"
  | "logout"
  | "pipeline_started"
  | "pipeline_completed"
  | "upload_started"
  | "upload_completed"
  // AGC-081 product analytics funnel
  | "Landing Page Viewed"
  | "Signup Started"
  | "Signup Completed"
  | "Email Verified"
  | "Login Success"
  | "Dashboard Viewed"
  | "Highlights Generated"
  | "Download Reel"
  | "Download Thumbnail"
  | "Upgrade Button Clicked"
  | "Checkout Started"
  | "Payment Success"
  | "Payment Failed"
  | "Logout";

// Analytics must never break the user flow — every call is wrapped so a
// PostHog/network failure is swallowed instead of propagating into caller code.
export function track(
  event: AnalyticsEvent,
  properties?: Record<string, unknown>
): void {
  if (typeof window === "undefined") return;
  try {
    posthog.capture(event, properties);
  } catch {
    // silent — analytics failures must never affect the app
  }
}

export function identify(
  userId: number | string,
  properties?: Record<string, unknown>,
  propertiesSetOnce?: Record<string, unknown>
): void {
  if (typeof window === "undefined") return;
  try {
    posthog.identify(String(userId), properties, propertiesSetOnce);
  } catch {
    // silent — analytics failures must never affect the app
  }
}

export function reset(): void {
  if (typeof window === "undefined") return;
  try {
    posthog.reset();
  } catch {
    // silent — analytics failures must never affect the app
  }
}
