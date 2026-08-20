// VED-GROWTH-001: pure show/hide decision for the ResultPanel upgrade CTA,
// extracted out of the component so this JSX-free module is directly
// testable with node:test — same pattern as utils/uploadPanelState.ts
// (this project has no jsdom/React-testing-library to render the
// component itself).

export interface ResultUpgradeCtaAvailability {
  isPro: boolean;
  subscriptionLoading: boolean;
}

export function shouldShowResultUpgradeCta({
  isPro,
  subscriptionLoading,
}: ResultUpgradeCtaAvailability): boolean {
  // Mirrors UploadPanel's outOfCredits gate: never show a plan-specific
  // CTA while the subscription is still resolving, to avoid a false
  // "upgrade" flash for a PRO user whose plan hasn't loaded yet.
  return !subscriptionLoading && !isPro;
}
