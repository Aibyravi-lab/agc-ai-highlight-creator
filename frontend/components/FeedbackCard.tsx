"use client";

import { useState } from "react";
import { submitFeedback } from "../services/api";
import { track } from "../services/analytics";

interface FeedbackCardProps {
  projectId?: number | null;
  onDismiss: () => void;
}

export function FeedbackCard({ projectId, onDismiss }: FeedbackCardProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [hoveredRating, setHoveredRating] = useState<number | null>(null);
  const [thumbs, setThumbs] = useState<"up" | "down" | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await submitFeedback({
        project_id: projectId ?? null,
        rating,
        thumbs,
        comment: comment.trim() || null,
      });
      track("Feedback Submitted", { rating, thumbs });
      setSubmitted(true);
      setTimeout(() => onDismiss(), 1500);
    } catch {
      // feedback submission is non-critical; dismiss after a brief delay
      setSubmitting(false);
      setTimeout(() => onDismiss(), 800);
    }
  };

  const handleSkip = () => {
    track("Feedback Skipped");
    onDismiss();
  };

  const displayRating = hoveredRating ?? rating;

  if (submitted) {
    return (
      <div className="border border-green-500/30 rounded-xl p-5 bg-green-950/20 text-center">
        <p className="text-green-400 text-sm font-medium">Thank you for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="border border-[#1a1d2e] rounded-xl p-5 bg-[#0d0f1a] space-y-4">
      <p className="text-sm font-medium text-white" id="feedback-heading">
        How was this highlight?
      </p>

      {/* Star rating */}
      <div className="flex gap-1" role="group" aria-labelledby="feedback-heading">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => setRating(n === rating ? null : n)}
            onMouseEnter={() => setHoveredRating(n)}
            onMouseLeave={() => setHoveredRating(null)}
            aria-label={`${n} star${n !== 1 ? "s" : ""}`}
            aria-pressed={rating !== null && n <= rating}
            className="text-2xl leading-none transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-yellow-400 rounded"
          >
            <span
              className={
                displayRating !== null && n <= displayRating
                  ? "text-yellow-400"
                  : "text-gray-600"
              }
            >
              ★
            </span>
          </button>
        ))}
      </div>

      {/* Thumbs */}
      <div className="flex gap-2">
        <button
          onClick={() => setThumbs(thumbs === "up" ? null : "up")}
          aria-label="Thumbs up"
          aria-pressed={thumbs === "up"}
          className={`text-lg px-3 py-1 rounded-lg border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 ${
            thumbs === "up"
              ? "border-green-500 text-green-400 bg-green-500/10"
              : "border-[#1a1d2e] text-gray-500 hover:border-[#2a2d3e] hover:text-gray-300"
          }`}
        >
          👍
        </button>
        <button
          onClick={() => setThumbs(thumbs === "down" ? null : "down")}
          aria-label="Thumbs down"
          aria-pressed={thumbs === "down"}
          className={`text-lg px-3 py-1 rounded-lg border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 ${
            thumbs === "down"
              ? "border-red-500 text-red-400 bg-red-500/10"
              : "border-[#1a1d2e] text-gray-500 hover:border-[#2a2d3e] hover:text-gray-300"
          }`}
        >
          👎
        </button>
      </div>

      {/* Comment */}
      <div>
        <label htmlFor="feedback-comment" className="sr-only">
          Optional comment
        </label>
        <textarea
          id="feedback-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Optional comment..."
          rows={2}
          maxLength={2000}
          className="w-full bg-[#0a0b14] border border-[#1a1d2e] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-[#2a2d3e] focus-visible:border-green-500/50"
        />
      </div>

      {/* Actions */}
      <div className="flex gap-3 items-center">
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="text-sm px-4 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-400"
        >
          {submitting ? "Submitting…" : "Submit"}
        </button>
        <button
          onClick={handleSkip}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-400 rounded"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
