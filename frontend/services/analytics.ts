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
  | "Feedback Skipped";

export function track(
  event: AnalyticsEvent,
  properties?: Record<string, unknown>
): void {
  if (typeof window === "undefined") return;
  posthog.capture(event, properties);
}

export function identify(userId: number | string): void {
  if (typeof window === "undefined") return;
  posthog.identify(String(userId));
}

export function reset(): void {
  if (typeof window === "undefined") return;
  posthog.reset();
}
