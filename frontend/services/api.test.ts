import { test } from "node:test";
import assert from "node:assert/strict";
import { mapHighlight, mapJob, getMaintenanceStatus, resolveMaintenanceState } from "./api.ts";

// AGC-082.1 — production regression: mapHighlight() dropped
// backendHighlight.explanation, so highlight.explanation.reasons was
// present in the downloaded result JSON but never reached ResultPanel.

test("mapHighlight preserves explanation.reasons from the backend payload", () => {
  const backendHighlight = {
    timestamp: 11,
    duration: 8,
    score: 0.741,
    action: "racing gameplay",
    category: "vehicle",
    clip_path: "clips/11.mp4",
    explanation: {
      reasons: [
        "High CLIP confidence",
        "Audio spike",
        "Category bonus applied",
        "Synergy activated",
      ],
    },
  };

  const mapped = mapHighlight(backendHighlight);

  assert.deepEqual(mapped.explanation, backendHighlight.explanation);
});

test("mapHighlight leaves explanation undefined when the backend omits it (older jobs)", () => {
  const mapped = mapHighlight({
    timestamp: 5,
    score: 0.5,
    action: "gameplay",
    category: "action",
  });

  assert.equal(mapped.explanation, undefined);
});

test("mapJob preserves explanation.reasons through the full backend job -> frontend job mapping path", () => {
  const backendJob = {
    job_id: "job-123",
    status: "completed",
    progress: 100,
    result: {
      title: "Epic Racing Moment",
      highlights_found: 1,
      all_highlights: [
        {
          timestamp: 11,
          duration: 8,
          score: 0.741,
          action: "racing gameplay",
          category: "vehicle",
          clip_path: "clips/11.mp4",
          explanation: {
            reasons: [
              "High CLIP confidence",
              "Audio spike",
              "Category bonus applied",
              "Synergy activated",
            ],
          },
        },
      ],
    },
  };

  const mappedJob = mapJob(backendJob);

  assert.deepEqual(
    mappedJob.result?.all_highlights?.[0]?.explanation?.reasons,
    backendJob.result.all_highlights[0].explanation.reasons
  );
});

// AGC-084 — maintenance mode: getMaintenanceStatus() is a thin,
// unauthenticated wrapper around GET /maintenance-status. Callers (the
// useMaintenanceStatus hook) are responsible for failing open on error;
// this layer must not swallow failures into a default value.

test("getMaintenanceStatus resolves { maintenance: true } when the backend reports maintenance ON", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ maintenance: true }), {
      status: 200,
    })) as typeof fetch;

  try {
    const result = await getMaintenanceStatus();
    assert.deepEqual(result, { maintenance: true });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("getMaintenanceStatus resolves { maintenance: false } when the backend reports maintenance OFF", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ maintenance: false }), {
      status: 200,
    })) as typeof fetch;

  try {
    const result = await getMaintenanceStatus();
    assert.deepEqual(result, { maintenance: false });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("getMaintenanceStatus rejects (does not default to a value) on network failure", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => {
    throw new Error("network down");
  }) as typeof fetch;

  try {
    await assert.rejects(() => getMaintenanceStatus());
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// AGC-084 CTO correction — true fail-open: a failed maintenance-status
// check must resolve to `false`, never preserve a stale `true`. Reasoning:
// if the last known state was maintenance=true and the status check
// fails after maintenance has actually ended, preserving `true` would
// leave the dashboard stuck showing the banner and disabling
// upload/generate indefinitely. The backend's 503 MAINTENANCE_MODE
// response remains the authoritative enforcement boundary if maintenance
// is genuinely still ON. resolveMaintenanceState is the pure function
// useMaintenanceStatus's polling effect delegates to for this decision.
// No jsdom/React-testing-library is set up in this project to render the
// hook itself, so this is exercised directly.

test("resolveMaintenanceState resolves true on a successful maintenance=true response", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ maintenance: true }), {
      status: 200,
    })) as typeof fetch;

  try {
    assert.equal(await resolveMaintenanceState(), true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("resolveMaintenanceState resolves false on a successful maintenance=false response", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ maintenance: false }), {
      status: 200,
    })) as typeof fetch;

  try {
    assert.equal(await resolveMaintenanceState(), false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("resolveMaintenanceState resolves false on network failure, even after a previous true state", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ maintenance: true }), {
        status: 200,
      })) as typeof fetch;
    assert.equal(await resolveMaintenanceState(), true);

    globalThis.fetch = (async () => {
      throw new Error("network down");
    }) as typeof fetch;
    assert.equal(await resolveMaintenanceState(), false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("resolveMaintenanceState resolves false on a non-OK HTTP response, even after a previous true state", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ maintenance: true }), {
        status: 200,
      })) as typeof fetch;
    assert.equal(await resolveMaintenanceState(), true);

    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: "Internal error" }), {
        status: 500,
      })) as typeof fetch;
    assert.equal(await resolveMaintenanceState(), false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
