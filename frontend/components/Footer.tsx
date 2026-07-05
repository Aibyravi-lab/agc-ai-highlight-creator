import Link from "next/link";

const FOOTER_LINKS: Array<{ label: string; href: string }> = [
  { label: "About", href: "/about" },
  { label: "Pricing", href: "/pricing" },
  { label: "Contact", href: "/contact" },
  { label: "Privacy", href: "/privacy" },
  { label: "Terms", href: "/terms" },
];

export function Footer() {
  return (
    <footer className="border-t border-[#1a1d2e] py-12">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 mb-8">
          <div>
            <span className="text-sm font-bold tracking-tight">Vedzovi</span>
            <p className="text-gray-500 text-xs mt-1">AI Video Highlight Generator</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {FOOTER_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-gray-500 hover:text-gray-300 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="border-t border-[#1a1d2e] pt-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span className="text-gray-600 text-xs">© 2026 Vedzovi</span>
          <span className="text-gray-700 text-xs">Public Beta</span>
        </div>
      </div>
    </footer>
  );
}
