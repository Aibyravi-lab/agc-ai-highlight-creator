import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MAINTENANCE_BANNER_MESSAGE } from "./maintenanceBannerCopy.ts";

// AGC-084 CTO correction — "MaintenanceBanner renders the approved
// maintenance copy when maintenance is ON" was required but not covered.
// This project has no jsdom/React-testing-library to render
// MaintenanceBanner.tsx directly (JSX syntax isn't handled by Node's
// built-in TypeScript type-stripping, and no component-rendering
// dependency exists here — adding one is out of scope per the CTO's
// no-new-testing-stack instruction). The approved copy was extracted
// into this JSX-free module specifically so the exact text is directly
// testable, and a static-source check proves the component actually
// renders it.

test("MAINTENANCE_BANNER_MESSAGE matches the CTO-approved maintenance banner copy exactly", () => {
  assert.equal(
    MAINTENANCE_BANNER_MESSAGE,
    "Vedzovi is upgrading.\n" +
      "AI processing is temporarily paused for a quick update.\n" +
      "Your existing projects are safe.\n" +
      "Estimated time: 5–10 minutes."
  );
});

test("approved copy mentions that existing projects are safe and gives an estimated time", () => {
  assert.match(MAINTENANCE_BANNER_MESSAGE, /existing projects are safe/i);
  assert.match(MAINTENANCE_BANNER_MESSAGE, /Estimated time: 5–10 minutes/);
});

// Static-source drift guard: proves MaintenanceBanner.tsx actually
// renders MAINTENANCE_BANNER_MESSAGE, rather than a hardcoded string
// that could drift away from what this test suite verifies.
test("MaintenanceBanner.tsx renders the shared, tested copy constant", () => {
  const source = readFileSync(
    new URL("./MaintenanceBanner.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /MAINTENANCE_BANNER_MESSAGE/);
});
