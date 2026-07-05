import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Terms & Conditions — Vedzovi",
  description: "The terms that govern your use of Vedzovi.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <InfoPageShell title="Terms & Conditions" subtitle="Last updated: July 2026">
      <InfoSection title="Acceptable Use">
        <p>
          You agree to use Vedzovi only for lawful purposes and to only upload content
          you have the right to use. You may not use the service to upload content
          that infringes on the rights of others or violates applicable laws.
        </p>
      </InfoSection>

      <InfoSection title="User Content">
        <p>
          You retain ownership of the videos and content you upload. By uploading
          content, you grant Vedzovi permission to process that content solely to
          provide the highlight generation service to you.
        </p>
      </InfoSection>

      <InfoSection title="Service Availability">
        <p>
          Vedzovi is provided on an &quot;as available&quot; basis. Features,
          processing times, and availability may change, particularly during the
          Public Beta period.
        </p>
      </InfoSection>

      <InfoSection title="Beta Disclaimer">
        <p>
          Vedzovi is currently in Public Beta. Functionality may be incomplete,
          unstable, or subject to change without notice. Highlight quality and
          processing results are not guaranteed.
        </p>
      </InfoSection>

      <InfoSection title="Limitation of Liability">
        <p>
          To the extent permitted by law, Vedzovi is not liable for any indirect,
          incidental, or consequential damages arising from use of the service.
        </p>
      </InfoSection>

      <InfoSection title="Termination">
        <p>
          We may suspend or terminate access to Vedzovi for accounts that violate
          these terms or misuse the service.
        </p>
      </InfoSection>
    </InfoPageShell>
  );
}
