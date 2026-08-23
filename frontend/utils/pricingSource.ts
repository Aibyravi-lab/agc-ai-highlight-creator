// VED-GROWTH-008: pure validation for the `source` attribution attached to
// pricing_page_viewed / Upgrade Button Clicked, extracted the same way
// uploadPanelState.ts / resultUpgradeCta.ts / firstUploadDiagnostics.ts were
// — this project has no jsdom/React-testing-library to render PricingPage
// directly, so the accept/reject decision is what's actually unit-tested.
// Additive-only metadata: it never changes navigation targets or event names.

export type PricingSource = "credits_exhausted" | "result_panel" | "direct";

// sessionStorage key a CTA writes just before navigating to /pricing, and
// that PricingPage reads (then clears) on mount to attribute the visit.
export const PRICING_CTA_SOURCE_KEY = "pricing_cta_source";

const VALID_CTA_SOURCES: ReadonlySet<string> = new Set<PricingSource>([
  "credits_exhausted",
  "result_panel",
]);

// Never trusts the raw sessionStorage value directly — anything missing or
// not one of the known CTA sources resolves to "direct".
export function resolvePricingSource(raw: string | null): PricingSource {
  if (raw !== null && VALID_CTA_SOURCES.has(raw)) {
    return raw as PricingSource;
  }
  return "direct";
}
