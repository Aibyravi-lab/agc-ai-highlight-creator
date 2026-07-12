import { MAINTENANCE_BANNER_MESSAGE } from "./maintenanceBannerCopy";

export function MaintenanceBanner() {
  return (
    <div
      role="status"
      className="flex items-start gap-3 rounded-2xl border border-blue-500/20 bg-blue-500/5 px-5 py-4"
    >
      <span className="text-blue-400 text-lg leading-none mt-0.5">🔧</span>
      <p className="text-sm text-blue-100/90 leading-relaxed whitespace-pre-line">
        {MAINTENANCE_BANNER_MESSAGE}
      </p>
    </div>
  );
}
