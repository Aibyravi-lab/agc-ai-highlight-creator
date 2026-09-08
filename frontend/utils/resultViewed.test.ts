import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("dashboard fires result_viewed only when a fresh non-null result arrives", () => {
  const source = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  const effect = source.match(
    /useEffect\(\(\) => \{\s*if \(result !== null && result !== prevResultRef\.current\) \{([\s\S]*?)prevResultRef\.current = result;\s*\}, \[result\]\);/
  );

  assert.ok(effect, "fresh-result effect not found");

  assert.match(effect[1], /track\("result_viewed", \{/);
  assert.match(effect[1], /highlights_found:/);
  assert.match(effect[1], /has_reel:/);
  assert.match(effect[1], /has_vertical_reel:/);
  assert.match(effect[1], /has_thumbnail:/);
});

test("result_viewed has exactly one frontend call site", () => {
  const dashboard = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  const calls = dashboard.match(/track\("result_viewed"/g) ?? [];
  assert.equal(calls.length, 1);
});

test("result_viewed is registered in the shared analytics event union", () => {
  const analytics = readFileSync(
    new URL("../services/analytics.ts", import.meta.url),
    "utf8"
  );

  assert.match(analytics, /\| "result_viewed"/);
});

test("existing feedback prompt remains tied to rendered results", () => {
  const dashboard = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  assert.match(
    dashboard,
    /\{result && \([\s\S]*?<FeedbackCard[\s\S]*?projectId=\{result\.project_id \?\? null\}/
  );
});
