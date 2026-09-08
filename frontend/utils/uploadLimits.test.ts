import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  MAX_UPLOAD_SIZE_MB,
  MAX_UPLOAD_SIZE_BYTES,
  MAX_VIDEO_DURATION_MINUTES,
  MAX_VIDEO_DURATION_SECONDS,
  isFileTooLarge,
  getFileTooLargeMessage,
  isVideoDurationTooLong,
  getVideoTooLongMessage,
  buildFileTooLargeEventProperties,
  buildVideoTooLongEventProperties,
} from "./uploadLimits.ts";

test("100 MB is within the limit", () => {
  assert.equal(isFileTooLarge(100 * 1024 * 1024), false);
});

test("2047 MB is within the limit", () => {
  assert.equal(isFileTooLarge(2047 * 1024 * 1024), false);
});

test("exactly 2048 MB is accepted (not strictly greater than the limit)", () => {
  assert.equal(isFileTooLarge(MAX_UPLOAD_SIZE_BYTES), false);
});

test("2049 MB is blocked", () => {
  assert.equal(isFileTooLarge(2049 * 1024 * 1024), true);
});

test("large-file error message reports the selected size and configured limit", () => {
  const message = getFileTooLargeMessage(6704.62 * 1024 * 1024);

  assert.match(message, /6\.5 GB/);
  assert.match(message, /2 GB/);
  assert.match(message, /2048 MB/);
  assert.match(message, /Trim or compress/);
});

test("large-file error message keeps sub-GB files in MB", () => {
  const message = getFileTooLargeMessage(500 * 1024 * 1024);

  assert.match(message, /500 MB/);
});

// --- isVideoDurationTooLong ---------------------------------------------

test("exactly 30 minutes (1800s) is accepted, not strictly greater than the limit", () => {
  assert.equal(isVideoDurationTooLong(1800), false);
});

test("1800.001 seconds (just over 30 minutes) is rejected", () => {
  assert.equal(isVideoDurationTooLong(1800.001), true);
});

test("1801 seconds is rejected", () => {
  assert.equal(isVideoDurationTooLong(1801), true);
});

test("1799 seconds (just under 30 minutes) is accepted", () => {
  assert.equal(isVideoDurationTooLong(1799), false);
});

test("0 seconds is accepted", () => {
  assert.equal(isVideoDurationTooLong(0), false);
});

test("NaN is not treated as too long (NaN comparisons are always false)", () => {
  assert.equal(isVideoDurationTooLong(NaN), false);
});

test("Infinity is treated as too long", () => {
  assert.equal(isVideoDurationTooLong(Infinity), true);
});

test("a negative duration is not treated as too long", () => {
  assert.equal(isVideoDurationTooLong(-5), false);
});

test("the 30-minute limit is derived from MAX_VIDEO_DURATION_MINUTES, not a duplicated literal", () => {
  // Regression guard: if MAX_VIDEO_DURATION_MINUTES ever changes, the
  // comparison threshold must move with it rather than staying pinned to 30.
  assert.equal(MAX_VIDEO_DURATION_SECONDS, MAX_VIDEO_DURATION_MINUTES * 60);
  assert.equal(isVideoDurationTooLong(MAX_VIDEO_DURATION_SECONDS), false);
  assert.equal(isVideoDurationTooLong(MAX_VIDEO_DURATION_SECONDS + 1), true);
});

test("duration-too-long error message mentions the 30 minute limit", () => {
  assert.match(getVideoTooLongMessage(), /30 minutes/);
});

// --- VED-GROWTH-008: rejection-telemetry property builders --------------
// Pure functions, so the "does it emit / does it not emit" behavior is
// proven at the boundary via isFileTooLarge / isVideoDurationTooLong above
// (already exhaustively tested) plus the static-source drift guards below,
// which prove usePipeline.ts's track() calls live strictly inside those
// exact gates. This file has no jsdom/File API, so the builders themselves
// are tested with plain byte/second numbers, same as the rest of this suite.

test("buildFileTooLargeEventProperties reports exact MB and the configured max", () => {
  assert.deepEqual(buildFileTooLargeEventProperties(2049 * 1024 * 1024), {
    file_size_mb: 2049,
    max_file_size_mb: MAX_UPLOAD_SIZE_MB,
  });
});

test("buildFileTooLargeEventProperties rounds file_size_mb to 2 decimal places", () => {
  const props = buildFileTooLargeEventProperties(2100000000);
  assert.equal(props.file_size_mb, 2002.72);
  assert.equal(props.max_file_size_mb, MAX_UPLOAD_SIZE_MB);
});

test("buildFileTooLargeEventProperties never includes a filename/path key", () => {
  const props = buildFileTooLargeEventProperties(2049 * 1024 * 1024);
  assert.deepEqual(Object.keys(props).sort(), ["file_size_mb", "max_file_size_mb"]);
});

test("buildVideoTooLongEventProperties reports duration, the configured max, and file size in MB", () => {
  assert.deepEqual(
    buildVideoTooLongEventProperties(1801, 100 * 1024 * 1024),
    {
      duration_seconds: 1801,
      max_duration_seconds: MAX_VIDEO_DURATION_SECONDS,
      file_size_mb: 100,
    }
  );
});

test("buildVideoTooLongEventProperties rounds a fractional duration to 2 decimal places", () => {
  const props = buildVideoTooLongEventProperties(1850.3456, 100 * 1024 * 1024);
  assert.equal(props.duration_seconds, 1850.35);
});

test("buildVideoTooLongEventProperties never includes a filename/path key", () => {
  const props = buildVideoTooLongEventProperties(1801, 100 * 1024 * 1024);
  assert.deepEqual(
    Object.keys(props).sort(),
    ["duration_seconds", "file_size_mb", "max_duration_seconds"]
  );
});

// --- Static-source drift guards ------------------------------------------
// usePipeline.ts is a hook with React state, not directly renderable in this
// project's jsdom-free node:test setup (same constraint as
// firstUploadDiagnostics.test.ts / resultUpgradeCta.test.ts). These guards
// prove the hook actually wires its two rejection branches to track() with
// the tested property builders, strictly inside the existing validation
// gates — so video_too_long/file_too_large can only fire exactly when
// isVideoDurationTooLong/isFileTooLarge are true, never unconditionally.

test("usePipeline.ts fires file_too_large exactly once, inside the isFileTooLarge gate", () => {
  const source = readFileSync(new URL("../hooks/usePipeline.ts", import.meta.url), "utf8");

  const gateMatch = source.match(
    /if \(isFileTooLarge\(file\.size\)\) \{([\s\S]*?)\n {6}\}/
  );
  assert.ok(gateMatch, "isFileTooLarge gate not found in usePipeline.ts");
  assert.match(
    gateMatch[1],
    /track\(\s*"file_too_large",\s*buildFileTooLargeEventProperties\(file\.size\)\s*\)/
  );

  const totalOccurrences = (source.match(/"file_too_large"/g) ?? []).length;
  assert.equal(totalOccurrences, 1, "file_too_large must be fired from exactly one call site");
});

test("usePipeline.ts fires video_too_long exactly once, inside the isVideoDurationTooLong gate", () => {
  const source = readFileSync(new URL("../hooks/usePipeline.ts", import.meta.url), "utf8");

  const gateMatch = source.match(
    /if \(durationSeconds !== null && isVideoDurationTooLong\(durationSeconds\)\) \{([\s\S]*?)\n {6}\}/
  );
  assert.ok(gateMatch, "isVideoDurationTooLong gate not found in usePipeline.ts");
  assert.match(
    gateMatch[1],
    /track\(\s*"video_too_long",\s*buildVideoTooLongEventProperties\(durationSeconds, file\.size\)\s*\)/
  );

  const totalOccurrences = (source.match(/"video_too_long"/g) ?? []).length;
  assert.equal(totalOccurrences, 1, "video_too_long must be fired from exactly one call site");
});

test("usePipeline.ts adds exactly two track() calls total (one per rejection branch, nowhere else)", () => {
  const source = readFileSync(new URL("../hooks/usePipeline.ts", import.meta.url), "utf8");
  const trackCalls = source.match(/track\(/g) ?? [];
  assert.equal(trackCalls.length, 2);
});

test("usePipeline.ts does not fire either rejection event from the null-duration fall-through path (fail-open preserved)", () => {
  const source = readFileSync(new URL("../hooks/usePipeline.ts", import.meta.url), "utf8");

  // The fail-open null check and its explanatory comment must still precede
  // the gate, unmodified by this change.
  assert.match(
    source,
    /durationSeconds !== null && isVideoDurationTooLong\(durationSeconds\)/
  );
  assert.match(source, /always falls through to the existing/);
  assert.match(source, /backend's ffprobe check remains authoritative/);
});

test("usePipeline.ts registers video_too_long and file_too_large in the shared track() union", () => {
  const source = readFileSync(new URL("../services/analytics.ts", import.meta.url), "utf8");
  assert.match(source, /"video_too_long"/);
  assert.match(source, /"file_too_large"/);
});

test("usePipeline.ts does not touch existing upload_started/Upload Started call sites (none exist client-side, per VED-ANALYTICS-005)", () => {
  const source = readFileSync(new URL("../hooks/usePipeline.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /track\("upload_started"/);
  assert.doesNotMatch(source, /track\("Upload Started"/);
});
