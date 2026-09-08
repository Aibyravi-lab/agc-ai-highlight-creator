import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("ResultPanel fires result_viewed after a non-null result reaches the UI", () => {
  const source = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  assert.match(
    source,
    /useEffect\(\(\) => \{\s*if \(!result\) return;[\s\S]*?track\("result_viewed", \{[\s\S]*?\}\);\s*\}, \[result\]\);/
  );

  assert.match(source, /highlights_found:/);
  assert.match(source, /has_reel:/);
  assert.match(source, /has_vertical_reel:/);
  assert.match(source, /has_thumbnail:/);
});

test("result_viewed has exactly one frontend call site", () => {
  const dashboard = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );
  const resultPanel = readFileSync(
    new URL("../components/ResultPanel.tsx", import.meta.url),
    "utf8"
  );

  const calls =
    (dashboard.match(/track\("result_viewed"/g) ?? []).length +
    (resultPanel.match(/track\("result_viewed"/g) ?? []).length;

  assert.equal(calls, 1);
});

test("dashboard no longer owns result_viewed reference-dedupe logic", () => {
  const dashboard = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  assert.doesNotMatch(dashboard, /prevResultRef/);
  assert.doesNotMatch(dashboard, /track\("result_viewed"/);
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


test("starting a new generation resets a previously dismissed feedback card", () => {
  const dashboard = readFileSync(
    new URL("../app/dashboard/page.tsx", import.meta.url),
    "utf8"
  );

  assert.match(
    dashboard,
    /const handleGenerateHighlights = async \(\) => \{\s*if \(selectedFile\) \{\s*[\s\S]*?setFeedbackDismissed\(false\);[\s\S]*?await generateHighlights\(selectedFile\);/
  );
});
