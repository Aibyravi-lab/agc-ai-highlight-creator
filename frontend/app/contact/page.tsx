import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Contact — Vedzovi",
  description: "Get in touch with the Vedzovi team.",
  path: "/contact",
});

const SUPPORT_EMAIL = "support@vedzovi.com";
const BUSINESS_EMAIL = "business@vedzovi.com";

export default function ContactPage() {
  return (
    <InfoPageShell title="Contact Us" subtitle="We're happy to help.">
      <InfoSection title="General Support">
        <p>
          For account issues, bug reports, or general questions, reach out at{" "}
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            {SUPPORT_EMAIL}
          </a>
          .
        </p>
      </InfoSection>

      <InfoSection title="Business">
        <p>
          For partnerships, press, or business inquiries, contact{" "}
          <a
            href={`mailto:${BUSINESS_EMAIL}`}
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            {BUSINESS_EMAIL}
          </a>
          .
        </p>
      </InfoSection>

      <InfoSection title="Response Time">
        <p>We typically respond within 24–48 hours.</p>
      </InfoSection>
    </InfoPageShell>
  );
}
