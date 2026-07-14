"use client";

import type { Segmentation } from "../../../types/missionControl";
import { SectionCard } from "./primitives";

export function SegmentationBanner({ segmentation }: { segmentation: Segmentation }) {
  return (
    <SectionCard padding="p-3 sm:p-4" className="border-cyan-500/20 bg-cyan-500/5">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
        <p className="text-xs font-semibold text-cyan-300 uppercase tracking-widest">
          External vs Internal/Test
        </p>
        <p className="text-xs text-gray-400">
          <span className="text-gray-200 font-semibold">{segmentation.external_users}</span> external users ·{" "}
          <span className="text-gray-200 font-semibold">{segmentation.internal_users}</span> internal/test users
        </p>
        <p className="text-xs text-gray-400">
          <span className="text-gray-200 font-semibold">{segmentation.external_jobs}</span> external jobs ·{" "}
          <span className="text-gray-200 font-semibold">{segmentation.internal_jobs}</span> internal/test jobs
          {segmentation.unattributed_jobs > 0 && (
            <>
              {" "}
              · <span className="text-gray-200 font-semibold">{segmentation.unattributed_jobs}</span> unattributed
            </>
          )}
        </p>
      </div>
      <p className="text-[11px] text-gray-500 mt-2">{segmentation.note}</p>
    </SectionCard>
  );
}
