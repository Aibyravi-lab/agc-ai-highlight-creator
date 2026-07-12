"use client";

import { useEffect, useState } from "react";
import { resolveMaintenanceState } from "../services/api";

const POLL_INTERVAL_MS = 5000;

/**
 * AGC-084: polls the public maintenance status endpoint while mounted.
 * Fails open to `false` on any check failure — see
 * resolveMaintenanceState. The backend's 503 MAINTENANCE_MODE response
 * on the actual upload/pipeline-start request remains the authoritative
 * enforcement boundary; this hook only drives the banner/disabled-state
 * UX.
 */
export function useMaintenanceStatus() {
  const [maintenance, setMaintenance] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      const next = await resolveMaintenanceState();
      if (!cancelled) setMaintenance(next);
    };

    check();
    const intervalId = setInterval(check, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  return maintenance;
}
