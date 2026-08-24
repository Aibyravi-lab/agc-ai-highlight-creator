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

// VED-GROWTH-008: minimal rejection telemetry. Property builders are pure
// (bytes/seconds in, plain numbers out) so they're testable with node:test
// without needing a File/browser environment — same rationale as
// isVideoDurationTooLong above. No filename, path, or file content is ever
// read or included.
function bytesToMb(bytes: number): number {
  return Math.round((bytes / (1024 * 1024)) * 100) / 100;
}

export interface FileTooLargeEventProperties {
  file_size_mb: number;
  max_file_size_mb: number;
  // Index signature: analytics.ts's track() takes Record<string, unknown>;
  // without this, TS rejects passing a named-interface value (as opposed to
  // an inline object literal) as that parameter.
  [key: string]: number;
}

export function buildFileTooLargeEventProperties(
  fileSizeBytes: number
): FileTooLargeEventProperties {
  return {
    file_size_mb: bytesToMb(fileSizeBytes),
    max_file_size_mb: MAX_UPLOAD_SIZE_MB,
  };
}

export interface VideoTooLongEventProperties {
  duration_seconds: number;
  max_duration_seconds: number;
  file_size_mb: number;
  // Index signature: analytics.ts's track() takes Record<string, unknown>;
  // without this, TS rejects passing a named-interface value (as opposed to
  // an inline object literal) as that parameter.
  [key: string]: number;
}

export function buildVideoTooLongEventProperties(
  durationSeconds: number,
  fileSizeBytes: number
): VideoTooLongEventProperties {
  return {
    duration_seconds: Math.round(durationSeconds * 100) / 100,
    max_duration_seconds: MAX_VIDEO_DURATION_SECONDS,
    file_size_mb: bytesToMb(fileSizeBytes),
  };
}
