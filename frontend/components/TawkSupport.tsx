"use client";

import { useEffect } from "react";
import Script from "next/script";
import { track } from "../services/analytics";

// VED-SUPPORT-001 — Founder Live Support MVP.
//
// Embeds the free tawk.to widget for HUMAN/founder live chat (not an AI bot).
// Only the PUBLIC widget embed identifiers are used here — these are safe to
// ship to the browser and are the same values tawk.to prints in its own
// copy-paste snippet. The tawk.to JavaScript API key is intentionally NOT
// used and must never be added to this file.
const TAWK_PROPERTY_ID = "6a9ffb9f0cdcdb34524abb3a";
const TAWK_WIDGET_ID = "1k20etqc7";
const TAWK_EMBED_SRC = `https://embed.tawk.to/${TAWK_PROPERTY_ID}/${TAWK_WIDGET_ID}`;

// Minimal shape of the tawk.to global we interact with. onChatMaximized is
// tawk.to's documented callback that fires when the visitor actually opens /
// maximizes the chat window — not when the script loads.
interface TawkApi {
  onChatMaximized?: () => void;
}

declare global {
  interface Window {
    Tawk_API?: TawkApi;
    Tawk_LoadStart?: Date;
  }
}

export function TawkSupport() {
  useEffect(() => {
    // Register the "chat opened" telemetry hook before the widget script
    // initializes. Direct assignment is idempotent, so a StrictMode double
    // effect invocation cannot double-fire the event.
    const tawk: TawkApi = window.Tawk_API ?? {};
    window.Tawk_API = tawk;
    window.Tawk_LoadStart = window.Tawk_LoadStart ?? new Date();
    tawk.onChatMaximized = () => {
      track("support_chat_opened");
    };
  }, []);

  // lazyOnload: tawk.to's own guidance and the Next.js docs both classify a
  // chat support plugin as a low-priority, load-during-idle script.
  return <Script id="tawk-to" src={TAWK_EMBED_SRC} strategy="lazyOnload" />;
}
