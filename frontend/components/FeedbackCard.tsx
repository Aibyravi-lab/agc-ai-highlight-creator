"use client";

import { useEffect, useState } from "react";
import { submitFeedback } from "../services/api";
import { track } from "../services/analytics";
import type { ImprovementArea } from "../types/pipeline";

interface FeedbackCardProps {
  projectId?: number | null;
  onDismiss: () => void;
}

const RATING_OPTIONS: { value: number; emoji: string; label: string }[] = [
  { value: 4, emoji: "🔥", label: "Great" },
  { value: 3, emoji: "👍", label: "Good" },
  { value: 2, emoji: "😐", label: "Okay" },
  { value: 1, emoji: "👎", label: "Bad" },
];

const IMPROVEMENT_AREA_OPTIONS: { value: ImprovementArea; label: string }[] = [
  { value: "highlight_selection", label: "Highlight selection" },
  { value: "clip_timing", label: "Clip timing" },
  { value: "processing_speed", label: "Processing speed" },
  { value: "captions", label: "Captions" },
  { value: "other", label: "Other" },
];

const COMMENT_MAX_LENGTH = 300;

export function FeedbackCard({ projectId, onDismiss }: FeedbackCardProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [improvementArea, setImprovementArea] = useState<ImprovementArea | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    track("feedback_prompt_viewed");
  }, []);

  const handleSelectRating = (value: number) => {
    setRating(value);
    track("feedback_rating_selected", { rating: value });
  };

  const handleSubmit = async () => {
    if (submitting || rating === null) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitFeedback({
        project_id: projectId ?? null,
        rating,
        improvement_area: improvementArea,
        comment: comment.trim() || null,
      });
      track("feedback_submitted", { rating, improvement_area: improvementArea });
      setSubmitted(true);
      setTimeout(() => onDismiss(), 1800);
    } catch (err) {
      // The card must only reach the submitted/dismissed state on a
      // confirmed POST /feedback success — dismissing here would hide a
      // failed submission behind what looks like a normal skip, with no
      // trace that feedback was lost.
      console.error("submitFeedback failed", err);
      setSubmitting(false);
      setSubmitError("Couldn't send feedback. Please try again.");
    }
  };

  if (submitted) {
    return (
      <div className="rounded-xl border border-green-500/30 bg-green-950/20 p-5 text-center">
        <p className="text-sm font-medium text-green-400">
          Thanks — you&apos;re helping improve Vedzovi AI.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-white" id="feedback-heading">
          How was your Vedzovi result?
        </p>
        <button
          onClick={onDismiss}
          aria-label="Dismiss feedback"
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-400 rounded shrink-0"
        >
          Not now
        </button>
      </div>

      {/* Rating */}
      <div className="flex flex-wrap gap-2" role="group" aria-labelledby="feedback-heading">
        {RATING_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => handleSelectRating(option.value)}
            aria-pressed={rating === option.value}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 ${
              rating === option.value
                ? "border-green-500 bg-green-500/10 text-white"
                : "border-[#1a1d2e] text-gray-400 hover:border-[#2a2d3e] hover:text-gray-200"
            }`}
          >
            <span className="text-lg leading-none" aria-hidden="true">
              {option.emoji}
            </span>
            <span>{option.label}</span>
          </button>
        ))}
      </div>

      {rating !== null && (
        <div className="space-y-4 pt-1">
          {/* Improvement area */}
          <div>
            <p className="text-xs text-gray-500 mb-2">What should we focus on? (optional)</p>
            <div className="flex flex-wrap gap-2">
              {IMPROVEMENT_AREA_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() =>
                    setImprovementArea(improvementArea === option.value ? null : option.value)
                  }
                  aria-pressed={improvementArea === option.value}
                  className={`px-3 py-1.5 rounded-full border text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 ${
                    improvementArea === option.value
                      ? "border-green-500 bg-green-500/10 text-white"
                      : "border-[#1a1d2e] text-gray-400 hover:border-[#2a2d3e] hover:text-gray-200"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Comment */}
          <div>
            <label htmlFor="feedback-comment" className="sr-only">
              What should Vedzovi improve?
            </label>
            <textarea
              id="feedback-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="What should Vedzovi improve? (optional)"
              rows={2}
              maxLength={COMMENT_MAX_LENGTH}
              className="w-full bg-[#0a0b14] border border-[#1a1d2e] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-[#2a2d3e] focus-visible:border-green-500/50"
            />
          </div>

          {/* Submit */}
          <div className="space-y-2">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="text-sm px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-400"
            >
              {submitting ? "Sending…" : "Send feedback"}
            </button>
            {submitError && (
              <p role="alert" className="text-xs text-red-400">
                {submitError}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
