import type { Metadata } from "next";
import { hasOgImage } from "./brandAssets";

export const SITE_NAME = "Vedzovi";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://vedzovi.com";

interface PageMetadataInput {
  title: string;
  description: string;
  path: string;
}

export function buildPageMetadata({ title, description, path }: PageMetadataInput): Metadata {
  // og-image.png is optional — only referenced once it actually exists in public/,
  // so we never point OG/Twitter tags at a missing file. See docs/branding-assets.md.
  const ogImageUrl = hasOgImage ? `${SITE_URL}/og-image.png` : undefined;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      siteName: SITE_NAME,
      url: path,
      type: "website",
      ...(ogImageUrl
        ? { images: [{ url: ogImageUrl, width: 1200, height: 630, alt: title }] }
        : {}),
    },
    twitter: {
      card: ogImageUrl ? "summary_large_image" : "summary",
      title,
      description,
      ...(ogImageUrl ? { images: [ogImageUrl] } : {}),
    },
  };
}
