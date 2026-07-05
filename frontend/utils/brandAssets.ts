import { existsSync } from "node:fs";
import { join } from "node:path";

const PUBLIC_DIR = join(process.cwd(), "public");

function publicAssetExists(filename: string): boolean {
  return existsSync(join(PUBLIC_DIR, filename));
}

// These flip to true automatically once the corresponding file is dropped into
// public/ — no code changes needed. See docs/branding-assets.md.
export const hasFavicon = publicAssetExists("favicon.ico");
export const hasAppleTouchIcon = publicAssetExists("apple-touch-icon.png");
export const hasOgImage = publicAssetExists("og-image.png");
