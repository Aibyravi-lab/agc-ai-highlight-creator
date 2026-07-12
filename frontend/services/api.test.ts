import { test } from "node:test";
import assert from "node:assert/strict";
import { mapHighlight, mapJob } from "./api.ts";

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
