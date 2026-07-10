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

test("499 MB is within the limit", () => {
  assert.equal(isFileTooLarge(499 * 1024 * 1024), false);
});

test("exactly 500 MB is accepted (not strictly greater than the limit)", () => {
  assert.equal(isFileTooLarge(MAX_UPLOAD_SIZE_BYTES), false);
});

test("501 MB is blocked", () => {
  assert.equal(isFileTooLarge(501 * 1024 * 1024), true);
});

test("error message mentions the 500 MB limit", () => {
  assert.match(getFileTooLargeMessage(), /500 MB/);
});
