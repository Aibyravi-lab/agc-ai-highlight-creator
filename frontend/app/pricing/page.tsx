"use client";

import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";

export default function PricingPage() {
  const { user, loading } = useAuth();
  const ctaHref = !loading && user ? "/dashboard" : "/register";

  return (
    <InfoPageShell
      title="Pricing"
      subtitle="Simple and transparent, currently free during Public Beta."
    >
      <InfoSection title="Public Beta">
        <p>
          Vedzovi is currently available as a Public Beta. All core features are
          currently free while we collect feedback and improve the platform.
        </p>
        <p>Paid plans will be introduced after Public Beta.</p>
      </InfoSection>

      <div>
        <Link
          href={ctaHref}
          className="inline-block bg-green-600 hover:bg-green-700 text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-colors"
        >
          Start Free
        </Link>
      </div>
    </InfoPageShell>
  );
}
