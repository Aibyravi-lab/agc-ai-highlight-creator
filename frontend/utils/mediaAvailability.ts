// VED-MEDIA-002: pure "is this generated media actually there" decision,
// extracted out of ProjectsPanel/HistoryPanel so it's directly testable
// with node:test (this project has no jsdom/React-testing-library to
// render the components themselves). A project/history row can persist a
// path whose file no longer exists on disk (see VED-MEDIA-001) -- the
// backend now returns an explicit *_available boolean alongside each
// path so the UI can distinguish "never generated" (path is null, no
// change from prior behavior) from "was generated but is now missing"
// (path set, available=false -- show "Media unavailable" instead of a
// silent broken thumbnail/no-op download).

export type MediaState = "available" | "unavailable" | "not_generated";

/**
 * `available` is treated as true whenever it is `true` or `undefined` --
 * only an explicit `false` from the backend marks media unavailable. This
 * keeps behavior unchanged (optimistic, matching the pre-VED-MEDIA-002
 * UI) for the brief window of a rolling deploy where the frontend has
 * shipped before the backend, and the field is simply absent.
 */
export function resolveMediaState(
  path: string | null | undefined,
  available: boolean | undefined
): MediaState {
  if (!path) return "not_generated";
  return available === false ? "unavailable" : "available";
}

export function isMediaUsable(
  path: string | null | undefined,
  available: boolean | undefined
): boolean {
  return resolveMediaState(path, available) === "available";
}

export const MEDIA_UNAVAILABLE_LABEL = "Media unavailable";
export const MEDIA_UNAVAILABLE_DESCRIPTION =
  "This generated media is no longer available.";
