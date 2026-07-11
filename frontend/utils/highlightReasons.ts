// Creator-facing priority order for AGC-084. Backend `explanation.reasons`
// is the canonical, unbounded trace — this only selects what to display.
const REASON_PRIORITY: readonly string[] = [
  "High CLIP confidence",
  "High motion",
  "Audio spike",
  "Scene change detected",
  "Category bonus applied",
  "Profile bonus applied",
  "Synergy activated",
];

const MAX_DISPLAY_REASONS = 4;

export function selectDisplayReasons(reasons?: string[]): string[] {
  if (!reasons || reasons.length === 0) {
    return [];
  }

  const present = new Set(reasons);

  return REASON_PRIORITY.filter((reason) => present.has(reason)).slice(
    0,
    MAX_DISPLAY_REASONS
  );
}
