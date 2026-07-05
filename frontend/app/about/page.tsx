import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "About — Vedzovi",
  description: "Learn what Vedzovi is, our mission, and why we built it.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <InfoPageShell
      title="About Vedzovi"
      subtitle="AI-powered highlights, built for creators."
    >
      <InfoSection title="What is Vedzovi?">
        <p>
          Vedzovi is an AI-powered video highlights platform that helps creators
          automatically discover the most exciting moments from long videos. Upload
          your gameplay or stream recording, and Vedzovi analyzes frames, audio, and
          scene content to surface the clips worth sharing.
        </p>
      </InfoSection>

      <InfoSection title="Our Mission">
        <p>
          Make highlight creation simple, fast, and accessible — so creators can spend
          less time scrubbing through raw footage and more time sharing their best
          moments.
        </p>
      </InfoSection>

      <InfoSection title="Why We Built It">
        <p>
          Turning hours of recordings into short, shareable clips is slow and
          repetitive when done by hand. We built Vedzovi to automate that process
          end-to-end — from detection to export — using AI instead of manual editing.
        </p>
      </InfoSection>

      <InfoSection title="Public Beta">
        <p>
          Vedzovi is currently in Public Beta. We&apos;re actively improving highlight
          quality and adding features based on user feedback, so some functionality is
          still evolving.
        </p>
      </InfoSection>
    </InfoPageShell>
  );
}
