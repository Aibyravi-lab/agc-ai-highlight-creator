import { test } from "node:test";
import assert from "node:assert/strict";
import { verifyEmail } from "./auth.ts";

// Activation-funnel friction fix: /auth/verify-email now additively
// returns the verified email (AGC-070 still withholds any access_token —
// see the comment on the backend route) so the frontend can pre-fill the
// sign-in form instead of asking the user to retype it from memory.

test("verifyEmail resolves { message, email } when the backend includes email", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({
        success: true,
        message: "Email verified successfully. You can now log in.",
        email: "player@example.com",
      }),
      { status: 200 }
    )) as typeof fetch;

  try {
    const result = await verifyEmail("some-token");
    assert.deepEqual(result, {
      message: "Email verified successfully. You can now log in.",
      email: "player@example.com",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("verifyEmail resolves with email undefined when the backend omits it", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({
        success: true,
        message: "Email verified successfully. You can now log in.",
      }),
      { status: 200 }
    )) as typeof fetch;

  try {
    const result = await verifyEmail("some-token");
    assert.equal(result.email, undefined);
    assert.equal(result.message, "Email verified successfully. You can now log in.");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("verifyEmail rejects on an invalid/expired token", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({ detail: "Invalid or expired verification token" }),
      { status: 400 }
    )) as typeof fetch;

  try {
    await assert.rejects(
      () => verifyEmail("bad-token"),
      /Invalid or expired verification token/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
