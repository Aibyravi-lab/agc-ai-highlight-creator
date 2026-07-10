// Mirrors backend/app/config/config.py MAX_UPLOAD_SIZE_MB / MAX_VIDEO_DURATION_MINUTES
// defaults. Kept as frontend constants purely to block guaranteed-to-fail
// uploads before they start; the backend remains the source of truth and
// re-validates independently.
export const MAX_UPLOAD_SIZE_MB = 500;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
export const MAX_VIDEO_DURATION_MINUTES = 30;

export function isFileTooLarge(fileSizeBytes: number): boolean {
  return fileSizeBytes > MAX_UPLOAD_SIZE_BYTES;
}

export function getFileTooLargeMessage(): string {
  return `This video exceeds the maximum upload size of ${MAX_UPLOAD_SIZE_MB} MB.`;
}
