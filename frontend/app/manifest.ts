import type { MetadataRoute } from "next";
import { SITE_NAME } from "../utils/seo";
import { hasAppleTouchIcon } from "../utils/brandAssets";

export default function manifest(): MetadataRoute.Manifest {
  const icons: MetadataRoute.Manifest["icons"] = [
    {
      src: "/favicon.ico",
      sizes: "any",
      type: "image/x-icon",
    },
  ];

  // Picked up automatically once public/apple-touch-icon.png is added.
  // See docs/branding-assets.md.
  if (hasAppleTouchIcon) {
    icons.push({
      src: "/apple-touch-icon.png",
      sizes: "180x180",
      type: "image/png",
    });
  }

  return {
    name: `${SITE_NAME} — AI Video Intelligence`,
    short_name: SITE_NAME,
    description: "Automatically turn long videos into shareable highlight clips with AI.",
    start_url: "/",
    display: "standalone",
    background_color: "#08090d",
    theme_color: "#08090d",
    icons,
  };
}
