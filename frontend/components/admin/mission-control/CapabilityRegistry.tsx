"use client";

import type { CapabilityCategory } from "../../../types/missionControl";
import { IconChevronDown } from "./icons";
import { SectionTitle } from "./primitives";

export function CapabilityRegistry({ registry }: { registry: CapabilityCategory[] }) {
  const totalCapabilities = registry.reduce((sum, group) => sum + group.capabilities.length, 0);

  return (
    <div>
      <SectionTitle>Capability Registry</SectionTitle>
      <details className="group rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden">
        <summary className="flex items-center justify-between px-4 py-3 cursor-pointer list-none hover:bg-white/[0.02] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:-outline-offset-2">
          <span className="text-sm text-gray-300">
            {totalCapabilities} production capabilities across {registry.length} categories
          </span>
          <IconChevronDown className="w-4 h-4 text-gray-500 shrink-0 ml-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="px-4 pb-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 border-t border-[#1e2030] pt-4">
          {registry.map((group) => (
            <div key={group.category} className="rounded-lg border border-[#1e2030] bg-[#0d0e14] p-3">
              <p className="text-sm font-semibold text-green-400 mb-2">{group.category}</p>
              <ul className="space-y-1.5">
                {group.capabilities.map((cap) => (
                  <li key={cap.name} className="text-sm">
                    <p className="text-gray-300">{cap.name}</p>
                    <p className="text-xs text-gray-600 font-mono truncate" title={cap.evidence}>
                      {cap.evidence}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
