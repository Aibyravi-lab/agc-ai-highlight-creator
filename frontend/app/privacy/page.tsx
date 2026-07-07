import type { Metadata } from "next";
import type { ReactNode } from "react";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "Privacy Policy — Vedzovi",
  description: "How Vedzovi collects, uses, and protects your information.",
  path: "/privacy",
});

const CONTACT_EMAIL = "contact@vedzovi.com";

function SubSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
      <div className="text-gray-400 text-sm leading-relaxed space-y-2">{children}</div>
    </div>
  );
}

export default function PrivacyPage() {
  return (
    <InfoPageShell title="Privacy Policy" subtitle="Last updated: July 2026">
      <InfoSection title="Introduction">
        <p>
          Vedzovi (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) provides an AI-powered
          platform that converts gaming videos and stream recordings into short-form
          highlight clips. This Privacy Policy explains what information we collect,
          how we use it, and the choices you have when you use Vedzovi.
        </p>
      </InfoSection>

      <InfoSection title="Information We Collect">
        <div className="space-y-5">
          <SubSection title="Account Information">
            <p>
              When you create an account, we collect basic details such as your name,
              email address, and authentication credentials, so we can identify you
              and secure your account.
            </p>
          </SubSection>

          <SubSection title="Uploaded Videos">
            <p>
              We store the video files you upload so that Vedzovi can process them and
              generate highlight clips, thumbnails, captions, and exports on your
              behalf. Uploaded videos remain associated with your account and are not
              shared with other users.
            </p>
          </SubSection>

          <SubSection title="AI Video Processing">
            <p>
              To detect highlight moments, Vedzovi analyzes video frames, audio, and
              scene content using automated AI models (including transcription,
              computer vision, and scoring). This processing happens to generate your
              clips and is not used to build a profile of you beyond your own account.
            </p>
          </SubSection>

          <SubSection title="Payment Metadata">
            <p>
              When you subscribe to a paid plan, we receive payment metadata such as
              transaction ID, payment status, plan selected, and amount charged.
              Payments are securely processed through Razorpay. Vedzovi never stores
              your:
            </p>
            <ul className="list-disc list-inside space-y-1 mt-2">
              <li>Card Number</li>
              <li>CVV</li>
              <li>UPI PIN</li>
              <li>Net Banking credentials</li>
            </ul>
            <p>
              This sensitive payment data is handled exclusively by Razorpay under its
              own security and compliance standards.
            </p>
          </SubSection>

          <SubSection title="Cookies">
            <p>
              Vedzovi may use cookies or local browser storage to keep you signed in
              and remember basic preferences. We do not use cookies for third-party
              advertising.
            </p>
          </SubSection>

          <SubSection title="Analytics">
            <p>
              We use privacy-conscious analytics to understand how Vedzovi is used
              (such as page views and feature usage) so we can improve the product.
              Analytics data is aggregated and is not sold to third parties.
            </p>
          </SubSection>
        </div>
      </InfoSection>

      <InfoSection title="How We Use Information">
        <ul className="list-disc list-inside space-y-1">
          <li>To operate, maintain, and improve the Vedzovi platform.</li>
          <li>To process uploaded videos and generate highlight clips.</li>
          <li>To manage your account, subscription, and billing.</li>
          <li>To communicate with you about your account or support requests.</li>
          <li>To detect, prevent, and address technical issues, abuse, or fraud.</li>
        </ul>
      </InfoSection>

      <InfoSection title="Security">
        <p>
          We take reasonable technical and organizational measures to help protect
          your data, including authentication safeguards on uploads and API access.
          No method of storage or transmission is completely secure, and we cannot
          guarantee absolute security.
        </p>
      </InfoSection>

      <InfoSection title="Data Retention">
        <p>
          We retain account information and uploaded content for as long as your
          account is active, or as needed to provide the service. You may request
          deletion of your data by contacting us, subject to any legal or accounting
          obligations to retain certain records.
        </p>
      </InfoSection>

      <InfoSection title="User Rights">
        <p>You may, at any time, request to:</p>
        <ul className="list-disc list-inside space-y-1 mt-2">
          <li>Access the personal information we hold about you.</li>
          <li>Correct inaccurate account information.</li>
          <li>Request deletion of your account and associated data.</li>
          <li>Withdraw consent for optional data processing, where applicable.</li>
        </ul>
        <p className="mt-2">
          To exercise any of these rights, contact us at{" "}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </InfoSection>

      <InfoSection title="Third Party Services">
        <p>
          Vedzovi relies on trusted third-party providers to operate the platform,
          including Razorpay for payment processing. These providers only receive the
          information necessary to perform their function and are bound by their own
          privacy and security obligations.
        </p>
      </InfoSection>

      <InfoSection title="Children's Privacy">
        <p>
          Vedzovi is not directed at children under the age of 13, and we do not
          knowingly collect personal information from children. If you believe a
          child has provided us with personal information, please contact us so we
          can remove it.
        </p>
      </InfoSection>

      <InfoSection title="Changes to Policy">
        <p>
          We may update this Privacy Policy from time to time to reflect changes in
          our practices or for legal, operational, or regulatory reasons. Material
          changes will be reflected by updating the &quot;Last updated&quot; date at
          the top of this page.
        </p>
      </InfoSection>

      <InfoSection title="Contact">
        <p>
          Questions about this policy can be sent to{" "}
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
