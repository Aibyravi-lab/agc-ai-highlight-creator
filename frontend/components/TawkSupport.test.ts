import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// VED-SUPPORT-001 — founder live-chat widget. This project has no
// jsdom/React-testing-library to render components directly (same
// constraint noted in utils/firstUploadDiagnostics.test.ts), so the widget
// wiring is verified with static-source assertions: the public embed
// identifiers, the single mount point in the root layout, the absence of
// any tawk.to JS API key, and the telemetry event registration.

const componentSource = readFileSync(
  new URL("./TawkSupport.tsx", import.meta.url),
  "utf8"
);
const layoutSource = readFileSync(
  new URL("../app/layout.tsx", import.meta.url),
  "utf8"
);
const analyticsSource = readFileSync(
  new URL("../services/analytics.ts", import.meta.url),
  "utf8"
);

test("component embeds the correct public tawk.to property and widget IDs", () => {
  assert.match(componentSource, /"6a9ffb9f0cdcdcb34524abb3a"/);
  assert.match(componentSource, /"1k20etqc7"/);
});

test("component builds the official tawk.to embed URL", () => {
  assert.match(
    componentSource,
    /https:\/\/embed\.tawk\.to\/\$\{TAWK_PROPERTY_ID\}\/\$\{TAWK_WIDGET_ID\}/
  );
});

test("component does not introduce a tawk.to JS API key or any secret", () => {
  assert.doesNotMatch(componentSource, /api[_-]?key/i);
  assert.doesNotMatch(componentSource, /secret/i);
});

test("component loads the widget via next/script in a client component", () => {
  assert.match(componentSource, /^"use client";/);
  assert.match(componentSource, /from "next\/script"/);
  assert.match(componentSource, /strategy="lazyOnload"/);
});

test("component fires support_chat_opened only from tawk.to's onChatMaximized hook", () => {
  assert.match(componentSource, /onChatMaximized/);
  assert.match(componentSource, /track\("support_chat_opened"\)/);
});

test("root layout mounts the support component exactly once", () => {
  assert.match(layoutSource, /import \{ TawkSupport \} from "\.\.\/components\/TawkSupport"/);
  const mountMatches = layoutSource.match(/<TawkSupport\s*\/>/g) ?? [];
  assert.equal(mountMatches.length, 1);
});

test("support_chat_opened is registered in the analytics event union", () => {
  assert.match(analyticsSource, /\|\s*"support_chat_opened"/);
});
