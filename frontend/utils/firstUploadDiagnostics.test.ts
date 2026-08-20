import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  hasZeroJobs,
  shouldTrackDashboardFirstVisitEmpty,
  shouldTrackUploadUiSeen,
} from "./firstUploadDiagnostics.ts";

// VED-GROWTH-001 Slice 2 — verified→first-upload diagnostic. Same pattern
// as utils/uploadPanelState.test.ts: this project has no jsdom/React-
// testing-library to render the dashboard/UploadPanel components directly,
// so the fire-once decisions are extracted into this JSX-free module and
// exercised here.

test("hasZeroJobs is false while jobStats hasn't loaded yet (null)", () => {
  assert.equal(hasZeroJobs(null), false);
});

test("hasZeroJobs is true when every job counter is zero", () => {
  assert.equal(
    hasZeroJobs({ queued: 0, running: 0, completed: 0, failed: 0 }),
    true
  );
});

test("hasZeroJobs is false when the user has any job in any state", () => {
  assert.equal(
    hasZeroJobs({ queued: 0, running: 0, completed: 1, failed: 0 }),
    false
  );
});

test("dashboard_first_visit_empty fires on an empty dashboard", () => {
  assert.equal(
    shouldTrackDashboardFirstVisitEmpty({
      jobStats: { queued: 0, running: 0, completed: 0, failed: 0 },
      alreadyTracked: false,
    }),
    true
  );
});

test("dashboard_first_visit_empty does not fire for a user with existing jobs", () => {
  assert.equal(
    shouldTrackDashboardFirstVisitEmpty({
      jobStats: { queued: 0, running: 0, completed: 3, failed: 0 },
      alreadyTracked: false,
    }),
    false
  );
});

test("dashboard_first_visit_empty does not fire while jobStats is still loading", () => {
  assert.equal(
    shouldTrackDashboardFirstVisitEmpty({ jobStats: null, alreadyTracked: false }),
    false
  );
});

test("dashboard_first_visit_empty does not re-fire once already tracked, even on a rerender with the same empty state", () => {
  assert.equal(
    shouldTrackDashboardFirstVisitEmpty({
      jobStats: { queued: 0, running: 0, completed: 0, failed: 0 },
      alreadyTracked: true,
    }),
    false
  );
});

test("upload_ui_seen fires when the upload UI is actually usable for a zero-job user", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: false,
    }),
    true
  );
});

test("upload_ui_seen does not fire for a user who already has jobs", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: false,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: false,
    }),
    false
  );
});

test("upload_ui_seen does not fire during maintenance mode, even for a zero-job user", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: true,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: false,
    }),
    false
  );
});

test("upload_ui_seen does not fire while subscription state is still loading", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: true,
      outOfCredits: false,
      alreadyTracked: false,
    }),
    false
  );
});

test("upload_ui_seen does not fire when credits are exhausted", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: true,
      alreadyTracked: false,
    }),
    false
  );
});

test("upload_ui_seen does not re-fire once already tracked", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: true,
    }),
    false
  );
});

// Static-source drift guards: prove the components actually wire their
// fire-once decisions to the tested functions above, rather than reverting
// to an inline/duplicated condition this suite would no longer cover.
test("dashboard/page.tsx sources dashboard_first_visit_empty from shouldTrackDashboardFirstVisitEmpty", () => {
  const source = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );
  assert.match(source, /shouldTrackDashboardFirstVisitEmpty/);
  assert.match(source, /"dashboard_first_visit_empty"/);
});

test("UploadPanel.tsx sources upload_ui_seen from shouldTrackUploadUiSeen and fires file_selected on selection", () => {
  const source = readFileSync(
    new URL("../components/UploadPanel.tsx", import.meta.url),
    "utf8"
  );
  assert.match(source, /shouldTrackUploadUiSeen/);
  assert.match(source, /"upload_ui_seen"/);
  assert.match(source, /"file_selected"/);
});
