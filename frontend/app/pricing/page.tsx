"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { useSubscription } from "../../hooks/useSubscription";
import { InfoPageShell } from "../../components/InfoPageShell";

interface PlanCardProps {
  name: string;
  price: string;
  priceSuffix?: string;
  features: string[];
  badge?: string;
  button: {
    label: string;
    href?: string;
    disabled?: boolean;
    onClick?: () => void;
  };
  highlighted?: boolean;
}

function PlanCard({ name, price, priceSuffix, features, badge, button, highlighted }: PlanCardProps) {
  return (
    <div
      className={`flex-1 bg-[#0d0e14] border rounded-2xl p-8 ${
        highlighted ? "border-green-500/30" : "border-[#1a1d2e]"
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-lg font-semibold text-white">{name}</h3>
        {badge && (
          <span className="text-xs bg-green-500/15 text-green-400 px-2 py-0.5 rounded-full font-medium">
            {badge}
          </span>
        )}
      </div>

      <div className="mb-6">
        <span className="text-3xl font-bold text-white">{price}</span>
        {priceSuffix && <span className="text-gray-500 text-sm">{priceSuffix}</span>}
      </div>

      <ul className="space-y-3 mb-8">
        {features.map((feature) => (
          <li key={feature} className="flex items-center gap-3 text-sm text-gray-400">
            <span className="w-4 h-4 rounded-full border border-green-500/30 bg-green-500/10 flex items-center justify-center flex-shrink-0">
              <svg viewBox="0 0 24 24" className="w-2.5 h-2.5 text-green-400" fill="none" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </span>
            {feature}
          </li>
        ))}
      </ul>

      {button.disabled ? (
        <span className="block text-center bg-[#1a1d2e] text-gray-500 font-semibold px-6 py-3 rounded-xl text-sm cursor-not-allowed">
          {button.label}
        </span>
      ) : button.onClick ? (
        <button
          onClick={button.onClick}
          className="block w-full text-center bg-green-600 hover:bg-green-700 text-white font-semibold px-6 py-3 rounded-xl text-sm transition-colors"
        >
          {button.label}
        </button>
      ) : (
        <Link
          href={button.href ?? "#"}
          className="block text-center bg-green-600 hover:bg-green-700 text-white font-semibold px-6 py-3 rounded-xl text-sm transition-colors"
        >
          {button.label}
        </Link>
      )}
    </div>
  );
}

export default function PricingPage() {
  const { user, loading: authLoading } = useAuth();
  const isAuthenticated = !authLoading && !!user;
  const { subscription, loading: subscriptionLoading, upgrade } = useSubscription(isAuthenticated);
  const router = useRouter();

  const [upgrading, setUpgrading] = useState(false);
  const [upgradeError, setUpgradeError] = useState<string | null>(null);

  // While auth or subscription is still resolving, we don't yet know the
  // user's plan — avoid rendering a plan-specific button prematurely.
  const isResolving = authLoading || (isAuthenticated && subscriptionLoading);
  const isPro = subscription?.plan === "PRO";

  const handleUpgrade = async () => {
    setUpgradeError(null);
    setUpgrading(true);
    try {
      await upgrade();
      router.push("/dashboard");
    } catch (err) {
      setUpgradeError(err instanceof Error ? err.message : "Upgrade failed. Please try again.");
      setUpgrading(false);
    }
  };

  return (
    <InfoPageShell
      title="Pricing"
      subtitle="Simple and transparent, currently free during Public Beta."
      backHref={isAuthenticated ? "/dashboard" : "/"}
      backLabel={isAuthenticated ? "← Back to Dashboard" : "← Back to Home"}
    >
      <div className="flex flex-col md:flex-row gap-6">
        <PlanCard
          name="Free"
          price="₹0"
          features={["3 AI Highlights", "Dashboard", "Projects", "History"]}
          button={
            isResolving
              ? { label: "Loading...", disabled: true }
              : isPro
              ? { label: "Free", disabled: true }
              : { label: "Current Plan", disabled: true }
          }
        />
        <PlanCard
          name="Pro"
          price="₹499"
          priceSuffix="/month"
          badge={!isResolving && isPro ? "Active" : undefined}
          highlighted
          features={["Unlimited AI Highlights", "Priority Processing", "Future Premium Features"]}
          button={
            isResolving
              ? { label: "Loading...", disabled: true }
              : isPro
              ? { label: "Current Plan", disabled: true }
              : isAuthenticated
              ? { label: upgrading ? "Upgrading..." : "Upgrade to Pro", onClick: handleUpgrade }
              : { label: "Sign in to Upgrade", href: "/login" }
          }
        />
      </div>

      {upgradeError && (
        <p className="mt-4 text-sm text-red-400 text-center">{upgradeError}</p>
      )}
    </InfoPageShell>
  );
}
