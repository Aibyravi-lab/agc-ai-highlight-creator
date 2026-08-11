import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MAX_UPLOAD_SIZE_BYTES,
  isFileTooLarge,
  getFileTooLargeMessage,
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
