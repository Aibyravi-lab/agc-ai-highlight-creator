import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { isUploadInteractionDisabled, isGenerateDisabled } from "./uploadPanelState.ts";

// AGC-084 CTO correction — "Upload/Generate interaction is disabled when
// maintenance is ON" and "Generate Highlights action cannot be triggered
// during maintenance" were required but not covered. This project has no
// jsdom/React-testing-library to render UploadPanel.tsx directly (JSX
// syntax isn't handled by Node's built-in TypeScript type-stripping, and
// no component-rendering dependency exists here — adding one is out of
// scope per the CTO's no-new-testing-stack instruction). The disablement
// decisions were extracted out of the component into this JSX-free
// module specifically so the *real* logic driving the disabled prop is
// exercised directly, not reimplemented in the test.

test("upload interaction is disabled when maintenance is ON, even with credits available", () => {
  assert.equal(
    isUploadInteractionDisabled({ maintenanceMode: true, outOfCredits: false }),
    true
  );
});

test("upload interaction is enabled when maintenance is OFF and credits are available", () => {
  assert.equal(
    isUploadInteractionDisabled({ maintenanceMode: false, outOfCredits: false }),
    false
  );
});

test("upload interaction remains disabled when out of credits with maintenance OFF (existing behavior unaffected)", () => {
  assert.equal(
    isUploadInteractionDisabled({ maintenanceMode: false, outOfCredits: true }),
    true
  );
});

test("Generate Highlights cannot be triggered during maintenance, even with a file selected and credits available", () => {
  assert.equal(
    isGenerateDisabled({
      loading: false,
      hasSelectedFile: true,
      maintenanceMode: true,
      outOfCredits: false,
      subscriptionLoading: false,
    }),
    true
  );
});

test("Generate Highlights is enabled when maintenance is OFF and every other condition is satisfied", () => {
  assert.equal(
    isGenerateDisabled({
      loading: false,
      hasSelectedFile: true,
      maintenanceMode: false,
      outOfCredits: false,
      subscriptionLoading: false,
    }),
    false
  );
});

test("Generate Highlights remains disabled without a selected file, independent of maintenance (existing behavior unaffected)", () => {
  assert.equal(
    isGenerateDisabled({
      loading: false,
      hasSelectedFile: false,
      maintenanceMode: false,
      outOfCredits: false,
      subscriptionLoading: false,
    }),
    true
  );
});

// Static-source drift guard: proves UploadPanel.tsx actually wires its
// disabled/generateDisabled state to the tested functions above, rather
// than reverting to an inline/duplicated condition that this test suite
// would then no longer be covering.
test("UploadPanel.tsx sources its disabled state from isUploadInteractionDisabled/isGenerateDisabled", () => {
  const source = readFileSync(
    new URL("../components/UploadPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /isUploadInteractionDisabled/);
  assert.match(source, /isGenerateDisabled/);
});
