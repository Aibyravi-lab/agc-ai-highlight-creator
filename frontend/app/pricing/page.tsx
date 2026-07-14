"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { useSubscription } from "../../hooks/useSubscription";
import { InfoPageShell } from "../../components/InfoPageShell";
import { createPaymentOrder, verifyPayment } from "../../services/api";
import { openRazorpayCheckout } from "../../services/razorpay";
import { track } from "../../services/analytics";
import type { RazorpayPaymentSuccess } from "../../types/payment";

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

      {button.onClick ? (
        <button
          onClick={button.onClick}
          disabled={button.disabled}
          className={`block w-full text-center font-semibold px-6 py-3 rounded-xl text-sm transition-colors ${
            button.disabled
              ? "bg-[#1a1d2e] text-gray-500 cursor-not-allowed"
              : "bg-green-600 hover:bg-green-700 text-white"
          }`}
        >
          {button.label}
        </button>
      ) : button.disabled ? (
        <span className="block text-center bg-[#1a1d2e] text-gray-500 font-semibold px-6 py-3 rounded-xl text-sm cursor-not-allowed">
          {button.label}
        </span>
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

type CheckoutState =
  | "idle"
  | "creating_order"
  | "opening_checkout"
  | "awaiting_payment"
  | "verifying"
  | "activating"
  | "done"
  | "cancelled"
  | "failed"
  | "verification_unconfirmed";

// States where a checkout/verification attempt is actively in flight —
// the Upgrade button stays disabled until we land back on a resting state
// (idle/cancelled/failed/done) so a second click can't fire a duplicate order.
const IN_FLIGHT_STATES: CheckoutState[] = [
  "creating_order",
  "opening_checkout",
  "awaiting_payment",
  "verifying",
  "activating",
  "done",
];

const CHECKOUT_LABELS: Partial<Record<CheckoutState, string>> = {
  creating_order: "Creating secure payment...",
  opening_checkout: "Opening Razorpay...",
  awaiting_payment: "Waiting for payment...",
  verifying: "Verifying payment...",
  activating: "Activating Pro...",
  done: "Done",
};

export default function PricingPage() {
  const { user, loading: authLoading } = useAuth();
  const isAuthenticated = !authLoading && !!user;
  const { subscription, loading: subscriptionLoading, refresh } = useSubscription(isAuthenticated);

  const [checkoutState, setCheckoutState] = useState<CheckoutState>("idle");
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [pendingPayment, setPendingPayment] = useState<RazorpayPaymentSuccess | null>(null);

  // Fires once per mount — mirrors the "Dashboard Viewed" / "Landing Page
  // Viewed" pattern. An empty dependency array means state/prop changes
  // from checkout progress never retrigger this.
  useEffect(() => {
    track("pricing_page_viewed");
  }, []);

  // While auth or subscription is still resolving, we don't yet know the
  // user's plan — avoid rendering a plan-specific button prematurely.
  const isResolving = authLoading || (isAuthenticated && subscriptionLoading);
  const isPro = subscription?.plan === "PRO";

  // Warn before leaving the page only while a verification request is
  // actually in flight — losing that request could leave a captured
  // payment unconfirmed. The warning disappears as soon as verification
  // settles (success or failure), matching the guard used for the retry flow.
  useEffect(() => {
    if (checkoutState !== "verifying") return;

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [checkoutState]);

  const runVerification = async (payment: RazorpayPaymentSuccess) => {
    setCheckoutState("verifying");

    try {
      await verifyPayment(payment);
      setCheckoutState("activating");
      await refresh();
      setPendingPayment(null);
      setCheckoutState("done");
      track("Payment Success");
    } catch {
      // Could be a genuine bad signature or a transient network/server
      // error — either way the payment was captured by Razorpay, so we
      // keep it around for a manual retry instead of forcing a new charge.
      setPendingPayment(payment);
      setCheckoutState("verification_unconfirmed");
    }
  };

  const handleRetryVerification = () => {
    if (!pendingPayment) return;
    runVerification(pendingPayment);
  };

  const handleUpgrade = async () => {
    if (IN_FLIGHT_STATES.includes(checkoutState)) return;

    track("Upgrade Button Clicked");
    setCheckoutError(null);
    setPendingPayment(null);
    setCheckoutState("creating_order");

    // Tracks which stage we're in so a caught error can be attributed to a
    // deterministic failure_category instead of guessing from message text.
    let stage: "order_creation_failed" | "checkout_failed" = "order_creation_failed";

    try {
      const order = await createPaymentOrder("pro");

      stage = "checkout_failed";
      setCheckoutState("opening_checkout");
      track("Checkout Started");
      await openRazorpayCheckout(order, {
        onSuccess: (payment) => {
          runVerification(payment);
        },
        onCancel: () => setCheckoutState("cancelled"),
        onFailure: (reason) => {
          setCheckoutError(reason);
          setCheckoutState("failed");
          track("Payment Failed", { reason, failure_category: "checkout_failed" });
        },
      });
      // Modal is open and awaiting user action — but if the user already
      // paid, cancelled, or failed faster than this line ran, don't clobber
      // whatever state the callback above already moved us to.
      setCheckoutState((state) => (state === "opening_checkout" ? "awaiting_payment" : state));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to start checkout. Please try again.";
      setCheckoutError(message);
      setCheckoutState("failed");
      track("Payment Failed", { reason: message, failure_category: stage });
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
          price="₹299"
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
              ? checkoutState === "verification_unconfirmed"
                ? { label: "Awaiting confirmation...", disabled: true }
                : {
                    label: CHECKOUT_LABELS[checkoutState] ?? "Upgrade to Pro",
                    onClick: handleUpgrade,
                    disabled: IN_FLIGHT_STATES.includes(checkoutState),
                  }
              : { label: "Sign in to Upgrade", href: "/login" }
          }
        />
      </div>

      {checkoutState === "done" && (
        <p className="mt-4 text-sm text-green-400 text-center">
          Payment verified! You&apos;re now on the Pro plan.
        </p>
      )}
      {checkoutState === "cancelled" && (
        <p className="mt-4 text-sm text-gray-400 text-center">Checkout cancelled.</p>
      )}
      {checkoutState === "failed" && checkoutError && (
        <p className="mt-4 text-sm text-red-400 text-center">{checkoutError}</p>
      )}
      {checkoutState === "verification_unconfirmed" && (
        <div className="mt-4 text-center">
          <p className="text-sm text-yellow-400 mb-2">
            We received your payment but couldn&apos;t confirm it yet.
          </p>
          <button
            onClick={handleRetryVerification}
            className="text-sm font-semibold text-green-400 hover:text-green-300 underline"
          >
            Retry Verification
          </button>
        </div>
      )}
    </InfoPageShell>
  );
}
