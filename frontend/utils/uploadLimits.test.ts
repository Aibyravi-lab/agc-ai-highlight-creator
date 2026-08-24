import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MAX_UPLOAD_SIZE_BYTES,
  MAX_VIDEO_DURATION_MINUTES,
  MAX_VIDEO_DURATION_SECONDS,
  isFileTooLarge,
  getFileTooLargeMessage,
  isVideoDurationTooLong,
  getVideoTooLongMessage,
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

test("error message mentions the 2048 MB limit", () => {
  assert.match(getFileTooLargeMessage(), /2048 MB/);
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
