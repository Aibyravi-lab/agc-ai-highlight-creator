import type { ReactNode } from "react";
import Link from "next/link";
import { Footer } from "./Footer";

interface InfoPageShellProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  backHref?: string;
  backLabel?: string;
}

export function InfoPageShell({
  title,
  subtitle,
  children,
  backHref = "/",
  backLabel = "← Back to Home",
}: InfoPageShellProps) {
  return (
    <div className="min-h-screen bg-[#08090d] text-white flex flex-col">
      <header className="border-b border-[#1a1d2e]">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold tracking-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">
            Vedzovi
          </Link>
          <Link
            href={backHref}
            className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded"
          >
            {backLabel}
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-3xl mx-auto px-6 py-14 sm:py-20">
          <h1 className="text-3xl md:text-4xl font-bold mb-3">{title}</h1>
          {subtitle && <p className="text-gray-400 text-lg mb-10">{subtitle}</p>}
          <div className="space-y-10">{children}</div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export function InfoSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section>
      <h2 className="text-lg font-semibold text-white mb-3">{title}</h2>
      <div className="text-gray-400 text-sm leading-relaxed space-y-3">{children}</div>
    </section>
  );
}
