"use client";

import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useSubscription } from "../hooks/useSubscription";
import { identify } from "../services/analytics";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const { subscription } = useSubscription(!loading && !!user);

  useEffect(() => {
    if (loading || !user) return;
    // $set user properties on every identify call — PostHog merges partial
    // updates, so this stays correct even before subscription data arrives.
    identify(
      user.id,
      {
        credits_remaining: user.credits_remaining,
        verified_email: user.email_verified,
        ...(subscription
          ? { plan: subscription.plan, subscription_status: subscription.status }
          : {}),
      },
      // set-once: initializes to false the first time this person is seen,
      // never overwrites it back to false once Upload Completed flips it true
      { first_upload_completed: false }
    );
  }, [user, loading, subscription]);

  return <>{children}</>;
}
