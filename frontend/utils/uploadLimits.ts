// Mirrors backend/app/config/config.py MAX_UPLOAD_SIZE_MB / MAX_VIDEO_DURATION_MINUTES
// defaults. Kept as frontend constants purely to block guaranteed-to-fail
// uploads before they start; the backend remains the source of truth and
// re-validates independently.
export const MAX_UPLOAD_SIZE_MB = 2048;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
export const MAX_VIDEO_DURATION_MINUTES = 30;
export const MAX_VIDEO_DURATION_SECONDS = MAX_VIDEO_DURATION_MINUTES * 60;

export function isFileTooLarge(fileSizeBytes: number): boolean {
  return fileSizeBytes > MAX_UPLOAD_SIZE_BYTES;
}

export function getFileTooLargeMessage(): string {
  return `This video exceeds the maximum upload size of ${MAX_UPLOAD_SIZE_MB} MB.`;
}

// VED-GROWTH-006: pure comparison only — reading a File's actual duration
// requires browser APIs and lives separately in utils/videoDuration.ts so
// this stays testable with plain node:test.
export function isVideoDurationTooLong(durationSeconds: number): boolean {
  return durationSeconds > MAX_VIDEO_DURATION_SECONDS;
}

export function getVideoTooLongMessage(): string {
  return `Video exceeds the maximum allowed duration of ${MAX_VIDEO_DURATION_MINUTES} minutes.`;
}
