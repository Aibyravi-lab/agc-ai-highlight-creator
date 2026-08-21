import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { getSafeLoginRedirect } from "./loginRedirect.ts";

// VED-GROWTH-007 — validates the `next` param used to send a user back to
// where they expressed upgrade intent (e.g. /pricing) after login, without
// letting it become an open redirect to another origin.

test("valid relative path /pricing is preserved", () => {
  assert.equal(getSafeLoginRedirect("/pricing"), "/pricing");
});

test("valid relative path /dashboard is preserved", () => {
  assert.equal(getSafeLoginRedirect("/dashboard"), "/dashboard");
});

test("missing next falls back to /dashboard", () => {
  assert.equal(getSafeLoginRedirect(null), "/dashboard");
});

test("empty string next falls back to /dashboard", () => {
  assert.equal(getSafeLoginRedirect(""), "/dashboard");
});

test("protocol-relative //evil.com is rejected as an open redirect and falls back to /dashboard", () => {
  assert.equal(getSafeLoginRedirect("//evil.com"), "/dashboard");
});

test("absolute URL is rejected and falls back to /dashboard", () => {
  assert.equal(getSafeLoginRedirect("https://evil.com"), "/dashboard");
});

test("path without a leading slash is rejected and falls back to /dashboard", () => {
  assert.equal(getSafeLoginRedirect("pricing"), "/dashboard");
});

// Static-source drift guards -------------------------------------------

test("login/page.tsx sources its post-login redirect target from getSafeLoginRedirect", () => {
  const source = readFileSync(new URL("../app/login/page.tsx", import.meta.url), "utf8");

  assert.match(source, /getSafeLoginRedirect/);
  assert.match(source, /searchParams\.get\("next"\)/);
  assert.match(source, /router\.replace\(redirectTarget\)/);
  // Neither redirect site should have reverted to a hardcoded "/dashboard".
  const hardcodedReplaces = source.match(/router\.replace\("\/dashboard"\)/g) ?? [];
  assert.equal(hardcodedReplaces.length, 0);
});

test("pricing/page.tsx sends the unauthenticated CTA through /login?next=/pricing", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(source, /href:\s*"\/login\?next=\/pricing"/);
});

test("pricing/page.tsx fires Upgrade Button Clicked with authenticated:false from the unauthenticated CTA, before navigation", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  const handlerMatch = source.match(
    /const handleSignInToUpgradeClick = \(\) => \{([\s\S]*?)\n {2}\};/
  );
  assert.ok(handlerMatch, "handleSignInToUpgradeClick handler not found in pricing/page.tsx");

  const handlerBody = handlerMatch[1];
  assert.match(
    handlerBody,
    /track\("Upgrade Button Clicked", \{ authenticated: false \}\)/
  );

  // Wired into the CTA's button config, not just declared and unused.
  assert.match(source, /onClick:\s*handleSignInToUpgradeClick/);
});

test("authenticated Upgrade Button Clicked call is unchanged (no properties added)", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  assert.match(source, /track\("Upgrade Button Clicked"\);/);
});

test("PlanCard renders href-based buttons as a navigating Link even when onClick is also present", () => {
  const source = readFileSync(new URL("../app/pricing/page.tsx", import.meta.url), "utf8");

  // The href branch must be checked before the onClick-only branch, otherwise
  // a button with both href and onClick would render as a non-navigating
  // <button> and "Sign in to Upgrade" would fire tracking but go nowhere.
  assert.match(
    source,
    /\{button\.href \? \([\s\S]{0,500}<Link[\s\S]{0,120}href=\{button\.href\}[\s\S]{0,60}onClick=\{button\.onClick\}/
  );
});
