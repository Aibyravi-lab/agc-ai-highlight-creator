// VED-GROWTH-006: reads a video File's duration client-side, before upload,
// using only native browser APIs (no new dependency). Requires a DOM/browser
// environment, so it is intentionally not covered by this project's
// node:test suite (no jsdom here — see uploadPanelState.test.ts) and is
// exercised at runtime instead. The pure duration *comparison* it feeds into
// (isVideoDurationTooLong in uploadLimits.ts) is unit tested separately.
//
// Resolves `null` — never rejects — when duration can't be reliably
// determined (metadata error, timeout, or a non-finite value some browsers
// report before a video is fully buffered). Callers must treat `null` as
// "unknown" and let the upload proceed; the backend's ffprobe check remains
// authoritative, so a false rejection here would be worse than a miss.
const READ_DURATION_TIMEOUT_MS = 10_000;

export function readVideoDurationSeconds(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    let objectUrl: string;

    try {
      objectUrl = URL.createObjectURL(file);
    } catch {
      resolve(null);
      return;
    }

    const video = document.createElement("video");
    video.preload = "metadata";

    let settled = false;
    const finish = (result: number | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("error", onError);
      URL.revokeObjectURL(objectUrl);
      resolve(result);
    };

    // CTO review: bounds the read so a browser that never fires
    // loadedmetadata/error (e.g. a malformed or unsupported file) can't
    // leave generateHighlights() awaiting this forever — timeout resolves
    // null, same fail-open path as a metadata error.
    const timeoutId = setTimeout(() => finish(null), READ_DURATION_TIMEOUT_MS);

    const onLoadedMetadata = () => {
      finish(Number.isFinite(video.duration) ? video.duration : null);
    };

    const onError = () => {
      finish(null);
    };

    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("error", onError);
    video.src = objectUrl;
  });
}
