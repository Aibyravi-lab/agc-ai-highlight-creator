import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolvePricingSource } from "./pricingSource.ts";

// VED-GROWTH-008 — additive attribution for which CTA sent a visitor to
// /pricing. Same pattern as uploadPanelState.test.ts / resultUpgradeCta.test.ts
// / firstUploadDiagnostics.test.ts: this project has no jsdom/React-testing-
// library to render UploadPanel/ResultPanel/PricingPage directly, so the
// pure accept/reject decision is what's actually unit-tested, plus static-
// source drift guards proving the components wire up to it.

test("credits_exhausted is accepted", () => {
  assert.equal(resolvePricingSource("credits_exhausted"), "credits_exhausted");
});

test("result_panel is accepted", () => {
  assert.equal(resolvePricingSource("result_panel"), "result_panel");
});

test("missing value (null) resolves to direct", () => {
  assert.equal(resolvePricingSource(null), "direct");
});

test("invalid/unrecognized value resolves to direct", () => {
  assert.equal(resolvePricingSource("something_else"), "direct");
});

test("empty string resolves to direct", () => {
  assert.equal(resolvePricingSource(""), "direct");
});

// Static-source drift guards -------------------------------------------

test("UploadPanel.tsx stores credits_exhausted before navigating, without changing the existing tracked event or href", () => {
  const source = readFileSync(
    new URL("../components/UploadPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /PRICING_CTA_SOURCE_KEY/);
  assert.match(
    source,
    /sessionStorage\.setItem\(PRICING_CTA_SOURCE_KEY, "credits_exhausted"\)/
  );
  // Existing event name and click tracking untouched.
  assert.match(source, /track\("credits_exhausted_cta_clicked"\)/);
  // Destination is still the plain /pricing route — no query string added.
  assert.match(source, /href="\/pricing"/);
  assert.doesNotMatch(source, /href="\/pricing\?/);
});

test("ResultPanel.tsx stores result_panel before navigating, without changing the existing tracked event or href", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /PRICING_CTA_SOURCE_KEY/);
  assert.match(
    source,
    /sessionStorage\.setItem\(PRICING_CTA_SOURCE_KEY, "result_panel"\)/
  );
  // Existing event name and click tracking untouched.
  assert.match(source, /track\("result_upgrade_cta_clicked"\)/);
  // Destination is still the plain /pricing route — no query string added.
  assert.match(source, /href="\/pricing"/);
  assert.doesNotMatch(source, /href="\/pricing\?/);
});

test("pricing/page.tsx reads and clears the attribution key on mount, and includes source on pricing_page_viewed", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(source, /resolvePricingSource\(sessionStorage\.getItem\(PRICING_CTA_SOURCE_KEY\)\)/);
  assert.match(source, /sessionStorage\.removeItem\(PRICING_CTA_SOURCE_KEY\)/);
  // Event name unchanged — only its properties gained `source`.
  assert.match(source, /track\("pricing_page_viewed", \{ source \}\)/);
  // No other call site fires pricing_page_viewed (still exactly once).
  const occurrences = (source.match(/"pricing_page_viewed"/g) ?? []).length;
  assert.equal(occurrences, 1);
});

test("pricing/page.tsx merges source into both Upgrade Button Clicked call sites without dropping authenticated:false", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(
    source,
    /const source = pricingSourceRef\.current;\s*\n\s*track\("Upgrade Button Clicked", \{ source \}\);/
  );
  assert.match(
    source,
    /track\("Upgrade Button Clicked", \{\s*\n\s*authenticated: false,\s*\n\s*source: pricingSourceRef\.current,\s*\n\s*\}\)/
  );
  // Event name itself is unchanged — still exactly "Upgrade Button Clicked"
  // at both call sites, no new event name introduced.
  const occurrences = (source.match(/"Upgrade Button Clicked"/g) ?? []).length;
  assert.equal(occurrences, 2);
});

// VED-GROWTH-008 refactor: source attribution must be read from a ref, not
// React state, so the mount effect never calls setState directly (that
// tripped the react-hooks/set-state-in-effect ESLint rule). This guard
// proves the refactor stuck rather than silently reverting under a future
// edit.
test("pricing/page.tsx uses a ref (not state) for pricingSource, so the mount effect never calls setState", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(source, /const pricingSourceRef = useRef<PricingSource>\("direct"\);/);
  assert.match(source, /pricingSourceRef\.current = source;/);
  assert.doesNotMatch(source, /useState<PricingSource>/);
  assert.doesNotMatch(source, /setPricingSource/);
});

test("Checkout Started and Payment Success/Failed event names are untouched by the attribution change", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(source, /track\("Checkout Started"\)/);
  assert.match(source, /track\("Payment Failed", \{ reason, failure_category: "checkout_failed" \}\)/);
  assert.match(source, /track\("Payment Failed", \{ reason: message, failure_category: stage \}\)/);
  // Payment Success is still fired server-side, not reintroduced client-side.
  assert.doesNotMatch(source, /track\("Payment Success"/);
});

test("analytics.ts track() union is unchanged — no new event names introduced by this change", () => {
  const source = readFileSync(new URL("../services/analytics.ts", import.meta.url), "utf8");

  // The attribution metadata rides on existing event names only.
  assert.doesNotMatch(source, /pricing_cta_source/);
  assert.doesNotMatch(source, /"credits_exhausted"/);
  assert.doesNotMatch(source, /"result_panel"/);
});
