"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import { useMissionControl } from "../../../hooks/useMissionControl";
import { MissionControlDashboard } from "../../../components/admin/MissionControlDashboard";

export default function MissionControlPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && (!user || !user.is_admin)) {
      router.replace("/dashboard");
    }
  }, [authLoading, user, router]);

  if (authLoading || !user || !user.is_admin) {
    return (
      <div className="min-h-screen bg-[#08090d] flex flex-col items-center justify-center gap-3">
        <div className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
        <p className="text-gray-500 text-sm">Loading Mission Control...</p>
      </div>
    );
  }

  return <MissionControlContent />;
}

function MissionControlContent() {
  const { summary, loading, error, lastUpdatedAt } = useMissionControl();

  return (
    <main className="min-h-screen bg-[#08090d] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-8">
        {error && (
          <div className="rounded-xl border border-red-500/25 bg-red-500/5 p-4">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {loading && !summary ? (
          <div className="min-h-[50vh] flex items-center justify-center gap-3 text-gray-500 text-sm">
            <div className="w-4 h-4 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
            Loading dashboard data...
          </div>
        ) : summary ? (
          <MissionControlDashboard summary={summary} lastUpdatedAt={lastUpdatedAt} />
        ) : null}
      </div>
    </main>
  );
}
