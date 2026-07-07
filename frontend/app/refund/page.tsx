import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Refund Policy — Vedzovi",
  description: "Vedzovi's refund and cancellation policy for subscriptions.",
  path: "/refund",
});

const CONTACT_EMAIL = "contact@vedzovi.com";

export default function RefundPage() {
  return (
    <InfoPageShell title="Refund Policy" subtitle="Last updated: July 2026">
      <InfoSection title="Subscriptions">
        <p>
          Vedzovi offers paid subscription plans (such as the PRO plan) billed on a
          recurring basis. Subscription charges are generally non-refundable once
          activated, except where required by applicable law.
        </p>
      </InfoSection>

      <InfoSection title="Cancellation">
        <p>
          You may cancel your subscription at any time from your account settings.
          Cancellation stops future billing, but does not entitle you to a refund for
          the current billing period already paid for. You will continue to have
          access to your paid plan until the end of the current billing cycle.
        </p>
      </InfoSection>

      <InfoSection title="Duplicate Payments">
        <p>
          If you were charged more than once for the same subscription period due to
          a technical or payment gateway error, contact us with your transaction
          details. Verified duplicate payments will be refunded in full to the
          original payment method via Razorpay.
        </p>
      </InfoSection>

      <InfoSection title="Failed Payments">
        <p>
          If a payment fails but an amount was deducted from your account, it is
          typically reversed automatically by your bank or Razorpay within a few
          business days. If the amount is not reversed, contact us with your
          transaction reference and we will investigate.
        </p>
      </InfoSection>

      <InfoSection title="Refund Requests">
        <p>
          To request a refund for a duplicate or failed payment, email us with your
          registered account email, the transaction ID, and the date of the charge.
          We review each request individually and aim to resolve valid requests
          within 7–10 business days.
        </p>
      </InfoSection>

      <InfoSection title="Support">
        <p>
          For any billing or refund questions, reach out to us at{" "}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </InfoSection>
    </InfoPageShell>
  );
}
