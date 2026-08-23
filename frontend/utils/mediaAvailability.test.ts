import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  resolveMediaState,
  isMediaUsable,
  MEDIA_UNAVAILABLE_LABEL,
  MEDIA_UNAVAILABLE_DESCRIPTION,
} from "./mediaAvailability.ts";

// VED-MEDIA-002 — same rationale as uploadPanelState.test.ts /
// resultUpgradeCta.test.ts: this project has no jsdom/React-testing-library
// to render ProjectsPanel.tsx/HistoryPanel.tsx directly, so the "is this
// generated media actually there" decision is extracted into a JSX-free
// pure function that IS directly testable, plus static-source drift guards
// proving both components actually wire their JSX to it.

test("path never generated (null) is not_generated, not unavailable", () => {
  assert.equal(resolveMediaState(null, undefined), "not_generated");
  assert.equal(resolveMediaState(undefined, undefined), "not_generated");
  assert.equal(resolveMediaState("", true), "not_generated");
});

test("path set and backend confirms available", () => {
  assert.equal(resolveMediaState("storage/jobs/x/reels/final.mp4", true), "available");
});

test("path set but backend confirms the file is missing", () => {
  assert.equal(resolveMediaState("storage/jobs/x/reels/final.mp4", false), "unavailable");
});

test("path set but availability flag not yet shipped by backend (undefined) fails open to available", () => {
  // Rolling-deploy safety: frontend deployed before backend still behaves
  // like pre-VED-MEDIA-002 (optimistic), not a false "unavailable" flash.
  assert.equal(resolveMediaState("storage/jobs/x/reels/final.mp4", undefined), "available");
});

test("isMediaUsable mirrors resolveMediaState's available case only", () => {
  assert.equal(isMediaUsable("path", true), true);
  assert.equal(isMediaUsable("path", false), false);
  assert.equal(isMediaUsable(null, true), false);
  assert.equal(isMediaUsable(undefined, undefined), false);
});

test("copy uses the CTO-approved neutral wording exactly", () => {
  assert.equal(MEDIA_UNAVAILABLE_LABEL, "Media unavailable");
  assert.equal(
    MEDIA_UNAVAILABLE_DESCRIPTION,
    "This generated media is no longer available."
  );
});

test("copy never implies deletion or a recovery promise", () => {
  const combined = `${MEDIA_UNAVAILABLE_LABEL} ${MEDIA_UNAVAILABLE_DESCRIPTION}`;
  assert.doesNotMatch(combined, /delet/i);
  assert.doesNotMatch(combined, /lost/i);
  assert.doesNotMatch(combined, /recover/i);
});

// Static-source drift guards -------------------------------------------

test("ProjectsPanel.tsx sources thumbnail/reel availability from resolveMediaState, not raw path truthiness", () => {
  const source = readFileSync(
    new URL("../components/ProjectsPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /resolveMediaState\(\s*\n?\s*project\.thumbnail_path/);
  assert.match(source, /resolveMediaState\(\s*\n?\s*project\.horizontal_reel_path/);
  assert.match(source, /MEDIA_UNAVAILABLE_LABEL/);
});

test("ProjectsPanel.tsx never fetches a thumbnail/reel path already confirmed unavailable", () => {
  const source = readFileSync(
    new URL("../components/ProjectsPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(
    source,
    /useAuthedMediaUrl\(\s*hasThumbnail \? project\.thumbnail_path : null\s*\)/
  );
  assert.match(
    source,
    /useAuthedMediaUrl\(hasReel \? project\.horizontal_reel_path : null\)/
  );
});

test("ProjectsPanel.tsx disables Open/Download Reel/Download Thumbnail using availability-derived flags", () => {
  const source = readFileSync(
    new URL("../components/ProjectsPanel.tsx", import.meta.url),
    "utf8"
  );

  const disabledAttrs = source.match(/disabled=\{![a-zA-Z]+\}/g) ?? [];
  assert.ok(disabledAttrs.includes("disabled={!hasReel}"));
  assert.ok(disabledAttrs.includes("disabled={!hasThumbnail}"));
});

test("HistoryPanel.tsx sources reel usability from isMediaUsable/resolveMediaState, not raw reel_path truthiness", () => {
  const source = readFileSync(
    new URL("../components/HistoryPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /isMediaUsable\(item\.reel_path, item\.reel_available\)/);
  assert.match(source, /resolveMediaState\(item\.reel_path, item\.reel_available\)/);
  assert.match(source, /MEDIA_UNAVAILABLE_LABEL/);
});

test("types/pipeline.ts declares the new availability fields the backend now sends", () => {
  const source = readFileSync(
    new URL("../types/pipeline.ts", import.meta.url),
    "utf8"
  );

  assert.match(source, /thumbnail_available:\s*boolean/);
  assert.match(source, /horizontal_reel_available:\s*boolean/);
  assert.match(source, /reel_available:\s*boolean/);
});

test("services/api.ts getHistory() forwards reel_available instead of dropping it", () => {
  const source = readFileSync(
    new URL("../services/api.ts", import.meta.url),
    "utf8"
  );

  assert.match(source, /reel_available:\s*item\.reel_available/);
});
