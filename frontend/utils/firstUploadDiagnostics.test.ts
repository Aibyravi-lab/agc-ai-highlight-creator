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

test("upload_ui_seen fires when the upload UI is actually usable for a zero-job user, after dashboard_first_visit_empty has already been tracked", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: false,
      dashboardFirstVisitEmptyTracked: true,
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
      dashboardFirstVisitEmptyTracked: true,
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
      dashboardFirstVisitEmptyTracked: true,
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
      dashboardFirstVisitEmptyTracked: true,
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
      dashboardFirstVisitEmptyTracked: true,
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
      dashboardFirstVisitEmptyTracked: true,
    }),
    false
  );
});

// VED-GROWTH-001 ordering fix regression coverage: upload_ui_seen must not
// fire ahead of dashboard_first_visit_empty even when every other gate is
// satisfied, since that's exactly the race that produced the broken funnel
// (Person 103: upload_ui_seen before dashboard_first_visit_empty).
test("upload_ui_seen does not fire before dashboard_first_visit_empty has been tracked, even when every other gate is satisfied", () => {
  assert.equal(
    shouldTrackUploadUiSeen({
      zeroJobs: true,
      maintenanceMode: false,
      subscriptionLoading: false,
      outOfCredits: false,
      alreadyTracked: false,
      dashboardFirstVisitEmptyTracked: false,
    }),
    false
  );
});

test("upload_ui_seen fires on the render after dashboard_first_visit_empty flips to tracked, once other gates are satisfied", () => {
  const availabilityExceptOrdering = {
    zeroJobs: true,
    maintenanceMode: false,
    subscriptionLoading: false,
    outOfCredits: false,
    alreadyTracked: false,
  };
  assert.equal(
    shouldTrackUploadUiSeen({
      ...availabilityExceptOrdering,
      dashboardFirstVisitEmptyTracked: false,
    }),
    false,
    "must not fire while dashboard_first_visit_empty is still untracked"
  );
  assert.equal(
    shouldTrackUploadUiSeen({
      ...availabilityExceptOrdering,
      dashboardFirstVisitEmptyTracked: true,
    }),
    true,
    "must fire once dashboard_first_visit_empty has been tracked"
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

// VED-GROWTH-001 ordering fix: prove the two components are actually wired
// together via dashboardFirstVisitEmptyTracked (state in the parent, prop
// into the child), not just that each still calls its own tracker in
// isolation — that wiring is the entire ordering fix.
test("dashboard/page.tsx tracks dashboard_first_visit_empty via state and passes it down as dashboardFirstVisitEmptyTracked", () => {
  const source = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );
  assert.match(source, /useState\(false\)/);
  assert.match(source, /dashboardFirstVisitEmptyTracked=\{dashboardFirstVisitEmptyTracked\}/);
});

test("UploadPanel.tsx requires dashboardFirstVisitEmptyTracked before evaluating upload_ui_seen", () => {
  const source = readFileSync(
    new URL("../components/UploadPanel.tsx", import.meta.url),
    "utf8"
  );
  assert.match(source, /dashboardFirstVisitEmptyTracked/);
});
