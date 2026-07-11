import { test } from "node:test";
import assert from "node:assert/strict";
import { selectDisplayReasons } from "./highlightReasons.ts";

test("undefined reasons (old jobs / missing explanation) returns empty array", () => {
  assert.deepEqual(selectDisplayReasons(undefined), []);
});

test("empty reasons array returns empty array", () => {
  assert.deepEqual(selectDisplayReasons([]), []);
});

test("caps at 4 reasons even when more are present", () => {
  const result = selectDisplayReasons([
    "High CLIP confidence",
    "High motion",
    "Audio spike",
    "Scene change detected",
    "Category bonus applied",
    "Profile bonus applied",
    "Synergy activated",
  ]);

  assert.equal(result.length, 4);
  assert.deepEqual(result, [
    "High CLIP confidence",
    "High motion",
    "Audio spike",
    "Scene change detected",
  ]);
});

test("sorts by CTO priority order regardless of input order", () => {
  const result = selectDisplayReasons([
    "Synergy activated",
    "Audio spike",
    "High CLIP confidence",
  ]);

  assert.deepEqual(result, [
    "High CLIP confidence",
    "Audio spike",
    "Synergy activated",
  ]);
});

test("filters out unknown/unrecognized reason strings", () => {
  const result = selectDisplayReasons([
    "High motion",
    "Some future reason not yet mapped",
  ]);

  assert.deepEqual(result, ["High motion"]);
});

test("does not fabricate reasons — only echoes what was passed in", () => {
  const result = selectDisplayReasons(["Profile bonus applied"]);

  assert.deepEqual(result, ["Profile bonus applied"]);
});
