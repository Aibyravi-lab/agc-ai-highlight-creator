import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Privacy Policy — Vedzovi",
  description: "How Vedzovi collects, uses, and protects your information.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <InfoPageShell title="Privacy Policy" subtitle="Last updated: July 2026">
      <InfoSection title="Information We Collect">
        <p>
          We collect the information necessary to operate Vedzovi, including account
          details you provide (such as your name and email address) and the video
          files you upload for processing.
        </p>
      </InfoSection>

      <InfoSection title="Uploaded Videos">
        <p>
          Videos you upload are stored in order to generate highlight clips and
          related outputs (thumbnails, captions, exported reels). Uploaded videos and
          generated files are associated with your account and are not shared with
          other users.
        </p>
      </InfoSection>

      <InfoSection title="Account Information">
        <p>
          We store basic account information, such as your name and email address, to
          authenticate you and manage your account.
        </p>
      </InfoSection>

      <InfoSection title="Cookies">
        <p>
          Vedzovi may use cookies or local browser storage to keep you signed in and
          remember basic preferences. We do not use cookies for third-party
          advertising.
        </p>
      </InfoSection>

      <InfoSection title="Security">
        <p>
          We take reasonable measures to help protect your data, including
          authentication safeguards on uploads and API access. No method of storage or
          transmission is completely secure, and we cannot guarantee absolute
          security.
        </p>
      </InfoSection>

      <InfoSection title="Data Retention">
        <p>
          We retain account information and uploaded content for as long as your
          account is active, or as needed to provide the service. You may request
          deletion of your data by contacting us.
        </p>
      </InfoSection>

      <InfoSection title="Contact">
        <p>
          Questions about this policy can be sent to{" "}
          <a
            href="mailto:support@vedzovi.com"
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            support@vedzovi.com
          </a>
          .
        </p>
      </InfoSection>
    </InfoPageShell>
  );
}
