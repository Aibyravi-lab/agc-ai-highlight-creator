import type { Metadata } from "next";
import { InfoPageShell, InfoSection } from "../../components/InfoPageShell";
import { buildPageMetadata } from "../../utils/seo";

export const metadata: Metadata = buildPageMetadata({
  title: "About — Vedzovi",
  description: "Learn what Vedzovi is, our mission, and why we built it.",
  path: "/about",
});

const CONTACT_EMAIL = "contact@vedzovi.com";

export default function AboutPage() {
  return (
    <InfoPageShell
      title="About Vedzovi"
      subtitle="AI-powered highlights, built for creators."
    >
      <InfoSection title="Who We Are">
        <p>
          Vedzovi is an AI-powered platform that turns long gaming videos and stream
          recordings into short, shareable highlight clips. We built Vedzovi for
          gamers and streamers who want to grow their audience without spending hours
          scrubbing through raw footage in an editor.
        </p>
      </InfoSection>

      <InfoSection title="Mission">
        <p>
          Our mission is to make highlight creation simple, fast, and accessible —
          so creators can spend less time editing and more time playing, streaming,
          and sharing their best moments with the world.
        </p>
      </InfoSection>

      <InfoSection title="Vision">
        <p>
          We believe every gamer should be able to turn their gameplay into
          scroll-stopping short-form content, regardless of editing skill or budget.
          Our vision is to become the fastest way for creators to go from raw footage
          to a published clip.
        </p>
      </InfoSection>

      <InfoSection title="What Vedzovi Does">
        <div className="space-y-5">
          <div>
            <h3 className="text-sm font-semibold text-white mb-2">
              AI Powered Video Highlights
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Vedzovi analyzes video frames, audio, and scene content using AI to
              automatically detect and score the most exciting moments in your
              footage, then packages them into ready-to-publish clips.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white mb-2">
              Built for Creators
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Every part of Vedzovi is designed around the workflow of gamers and
              streamers — upload your recording, let the AI pipeline do the work, and
              export clips formatted for YouTube Shorts, Instagram Reels, and TikTok.
            </p>
          </div>
        </div>
      </InfoSection>

      <InfoSection title="Future Roadmap">
        <p>
          Vedzovi is in active development. We&apos;re continuously improving
          highlight detection quality, expanding editing and export options, and
          adding new AI capabilities based on feedback from our creator community.
        </p>
      </InfoSection>

      <InfoSection title="Contact">
        <p>
          Have questions or feedback? Reach out at{" "}
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
