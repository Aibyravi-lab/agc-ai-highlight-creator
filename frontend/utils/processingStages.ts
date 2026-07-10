// Maps raw backend progress status/messages to human-friendly display text.
// Purely presentational — does not affect polling, progress values, or job state.

const FRIENDLY_STAGE_MESSAGES: Array<{ match: RegExp; message: string }> = [
  { match: /uploading/i, message: "Uploading your video..." },
  { match: /starting/i, message: "Preparing your video..." },
  { match: /extracting frames/i, message: "Extracting video frames..." },
  { match: /detecting highlights/i, message: "AI is analyzing your gameplay..." },
  { match: /fine scan/i, message: "Scoring highlights..." },
  { match: /generating reel/i, message: "Generating highlight clips..." },
  { match: /transcribing audio/i, message: "Analyzing audio and dialogue..." },
  { match: /adding captions/i, message: "Preparing your download..." },
  { match: /completed/i, message: "Your highlights are ready!" },
  { match: /queued/i, message: "Waiting to start..." },
  { match: /processing/i, message: "AI is analyzing your video..." },
];

export function getFriendlyStageMessage(rawStatus: string): string {
  if (!rawStatus) return "Processing your video...";
  const match = FRIENDLY_STAGE_MESSAGES.find((entry) => entry.match.test(rawStatus));
  return match ? match.message : rawStatus;
}
