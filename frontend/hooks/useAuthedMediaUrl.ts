"use client";

import { useEffect, useState } from "react";
import { fetchAuthedMediaUrl } from "../services/api";

/**
 * Resolves a stored file path (reel, thumbnail, clip) to a local object URL
 * via the authenticated /files/ endpoint, for use in <img>/<video> src
 * attributes. Returns null while loading, on error, or when path is empty.
 */
export function useAuthedMediaUrl(
  path: string | null | undefined
): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setUrl(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    fetchAuthedMediaUrl(path)
      .then((resolvedUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(resolvedUrl);
          return;
        }
        objectUrl = resolvedUrl;
        setUrl(resolvedUrl);
      })
      .catch(() => {
        if (!cancelled) setUrl(null);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  return url;
}
