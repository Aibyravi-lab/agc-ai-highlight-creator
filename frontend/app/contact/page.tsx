import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Contact — Vedzovi",
  description: "Get in touch with the Vedzovi team.",
  path: "/contact",
});

const CONTACT_EMAIL = "contact@vedzovi.com";

export default function ContactPage() {
  return (
    <InfoPageShell title="Contact Us" subtitle="Vedzovi — AI Video Highlight Generator">
      <InfoSection title="Email">
        <p>
          For account issues, billing questions, or general support, reach out at{" "}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </InfoSection>

      <InfoSection title="Business Hours">
        <p>Monday–Friday</p>
        <p>9 AM – 6 PM IST</p>
      </InfoSection>

      <InfoSection title="Response Time">
        <p>We typically respond within 24–48 business hours.</p>
      </InfoSection>
    </InfoPageShell>
  );
}
