import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { shouldShowResultUpgradeCta } from "./resultUpgradeCta.ts";

// VED-GROWTH-001 — same rationale as uploadPanelState.test.ts: this project
// has no jsdom/React-testing-library to render ResultPanel.tsx directly, so
// the show/hide decision is extracted into a JSX-free pure function that IS
// directly testable, plus static-source drift guards proving the component
// actually wires its JSX to this function (and to the click handler) rather
// than reimplementing the condition inline.

test("upgrade CTA is hidden for a PRO user", () => {
  assert.equal(
    shouldShowResultUpgradeCta({ isPro: true, subscriptionLoading: false }),
    false
  );
});

test("upgrade CTA is shown for a FREE user once subscription has resolved", () => {
  assert.equal(
    shouldShowResultUpgradeCta({ isPro: false, subscriptionLoading: false }),
    true
  );
});

test("upgrade CTA is hidden while subscription is still loading, even if plan is not yet known to be PRO", () => {
  assert.equal(
    shouldShowResultUpgradeCta({ isPro: false, subscriptionLoading: true }),
    false
  );
});

test("upgrade CTA stays hidden for a PRO user even if subscriptionLoading is stale-true", () => {
  assert.equal(
    shouldShowResultUpgradeCta({ isPro: true, subscriptionLoading: true }),
    false
  );
});

// Static-source drift guards -------------------------------------------

test("ResultPanel.tsx sources its upgrade-CTA visibility from shouldShowResultUpgradeCta", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /shouldShowResultUpgradeCta/);
  assert.match(source, /\{showUpgradeCta && \(/);
});

test("ResultPanel.tsx upgrade CTA navigates through the existing /pricing route, not a new payment route", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /href="\/pricing"[\s\S]{0,120}onClick=\{handleUpgradeCtaClick\}/);
});

test("ResultPanel.tsx fires result_upgrade_cta_clicked exactly once per CTA click, only on click", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  const handlerMatch = source.match(
    /const handleUpgradeCtaClick = \(\) => \{([\s\S]*?)\n {2}\};/
  );
  assert.ok(handlerMatch, "handleUpgradeCtaClick handler not found in ResultPanel.tsx");

  const handlerBody = handlerMatch[1];
  const trackCallsInHandler = handlerBody.match(/track\(/g) ?? [];
  assert.equal(trackCallsInHandler.length, 1);
  assert.match(handlerBody, /track\("result_upgrade_cta_clicked"\)/);

  // The event name must appear exactly once in the whole file — fired only
  // from the click handler, never from a mount/view effect (the primary
  // experiment here is CLICK -> UPGRADE -> PAYMENT, not a view event).
  const totalOccurrences = (
    source.match(/result_upgrade_cta_clicked/g) ?? []
  ).length;
  assert.equal(totalOccurrences, 1);
});

test("ResultPanel.tsx registers the new analytics event in the shared track() union", () => {
  const source = readFileSync(
    new URL("../services/analytics.ts", import.meta.url),
    "utf8"
  );

  assert.match(source, /"result_upgrade_cta_clicked"/);
});

test("existing download tracking (Download Reel / Download Thumbnail) is untouched by the CTA change", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  const downloadReelCalls = source.match(/track\("Download Reel"\)/g) ?? [];
  const downloadThumbnailCalls = source.match(/track\("Download Thumbnail"\)/g) ?? [];

  assert.equal(downloadReelCalls.length, 2);
  assert.equal(downloadThumbnailCalls.length, 1);
});

test("dashboard passes plan/credit state into ResultPanel so it can decide FREE vs PRO itself", () => {
  const source = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  assert.match(
    source,
    /<ResultPanel[\s\S]{0,200}isPro=\{isPro\}[\s\S]{0,200}\/>/
  );
});
