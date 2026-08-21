// VED-GROWTH-007: validates the `next` search param used to send a user
// back to where they expressed upgrade intent (e.g. /pricing) after login,
// without allowing it to be turned into an open redirect to another origin.

const DEFAULT_LOGIN_REDIRECT = "/dashboard";

export function getSafeLoginRedirect(next: string | null): string {
  if (!next) return DEFAULT_LOGIN_REDIRECT;
  if (!next.startsWith("/")) return DEFAULT_LOGIN_REDIRECT;
  if (next.startsWith("//")) return DEFAULT_LOGIN_REDIRECT;
  return next;
}
