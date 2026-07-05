import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "../context/AuthContext";
import { PostHogProvider } from "../components/PostHogProvider";
import { buildPageMetadata, SITE_NAME, SITE_URL } from "../utils/seo";
import { hasAppleTouchIcon, hasFavicon } from "../utils/brandAssets";
import "./globals.css";

// Only set metadata.icons once a custom asset exists in public/ — otherwise
// omit it so Next's default app/favicon.ico file-convention keeps serving.
// See docs/branding-assets.md.
const customIcons =
  hasFavicon || hasAppleTouchIcon
    ? {
        ...(hasFavicon ? { icon: "/favicon.ico" } : {}),
        ...(hasAppleTouchIcon ? { apple: "/apple-touch-icon.png" } : {}),
      }
    : undefined;

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: SITE_NAME,
  keywords: [
    "AI video highlights",
    "gaming highlight generator",
    "gameplay clip generator",
    "AI video editor",
    "YouTube Shorts generator",
    "TikTok clip generator",
    "Instagram Reels generator",
    "stream highlight maker",
    "automatic video clipping",
  ],
  ...buildPageMetadata({
    title: "Vedzovi — AI Video Intelligence",
    description: "Automatically turn long videos into shareable highlight clips with AI.",
    path: "/",
  }),
  ...(customIcons ? { icons: customIcons } : {}),
};

export const viewport: Viewport = {
  themeColor: "#08090d",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <PostHogProvider>{children}</PostHogProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
