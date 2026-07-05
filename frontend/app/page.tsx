"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../context/AuthContext";
import { track } from "../services/analytics";
import { Footer } from "../components/Footer";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  useEffect(() => {
    track("Landing Viewed");
  }, []);

  return (
    <div className="min-h-screen bg-[#08090d] text-white">
      <Nav />
      <Hero />
      <ProductShowcase />
      <BeforeAfter />
      <HowItWorks />
      <AITimeline />
      <Features />
      <ResultsSection />
      <TrustSection />
      <Platforms />
      <FAQ />
      <BetaNotice />
      <FinalCTA />
      <Footer />
    </div>
  );
}

// ─── Navbar ───────────────────────────────────────────────────────────────────

function Nav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <nav className="sticky top-0 z-50 bg-[#08090d]/95 backdrop-blur border-b border-[#1a1d2e]">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight">Vedzovi</span>
          <span className="hidden sm:block text-xs text-gray-500">AI Video Intelligence</span>
        </div>

        <div className="hidden md:flex items-center gap-7">
          <a href="#showcase" className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">Product</a>
          <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">Features</a>
          <a href="#how-it-works" className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">How it Works</a>
          <a href="#faq" className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">FAQ</a>
          <a href="#beta" className="text-sm text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded">Beta</a>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="hidden sm:block text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={() => track("Login Clicked")}
          >
            Login
          </Link>
          <Link
            href="/register"
            className="text-sm bg-green-600 hover:bg-green-700 text-white font-semibold px-4 py-2 rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-300"
            onClick={() => track("Register Clicked")}
          >
            Start Free Beta
          </Link>
          <button
            type="button"
            className="md:hidden flex items-center justify-center w-9 h-9 text-gray-400 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            {mobileMenuOpen ? <IconClose /> : <IconMenu />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#1a1d2e] bg-[#08090d] px-6 py-4 flex flex-col gap-1">
          <Link
            href="/login"
            className="px-2 py-2.5 text-sm text-gray-300 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={() => {
              track("Login Clicked");
              closeMobileMenu();
            }}
          >
            Login
          </Link>
          <Link
            href="/register"
            className="px-2 py-2.5 text-sm text-gray-300 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={() => {
              track("Register Clicked");
              closeMobileMenu();
            }}
          >
            Register
          </Link>
          <Link
            href="/pricing"
            className="px-2 py-2.5 text-sm text-gray-300 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={closeMobileMenu}
          >
            Pricing
          </Link>
          <Link
            href="/about"
            className="px-2 py-2.5 text-sm text-gray-300 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={closeMobileMenu}
          >
            About
          </Link>
          <Link
            href="/contact"
            className="px-2 py-2.5 text-sm text-gray-300 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:rounded-lg"
            onClick={closeMobileMenu}
          >
            Contact
          </Link>
        </div>
      )}
    </nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-24 md:py-32 flex flex-col md:flex-row items-center gap-16">
      <div className="flex-1 text-center md:text-left">
        <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-full px-4 py-1.5 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          <span className="text-xs text-green-400 font-medium">Public Beta — Now Open</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
          Turn Hours of Footage
          <br />
          <span className="text-green-400">into Viral Highlights</span>
        </h1>

        <p className="text-gray-400 text-lg leading-relaxed mb-10 max-w-lg mx-auto md:mx-0">
          Upload your video and let AI automatically detect the most exciting moments,
          ready for Shorts, Reels and TikTok.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center md:justify-start mb-10">
          <Link
            href="/register"
            className="bg-green-600 hover:bg-green-700 text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-colors text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-300"
            onClick={() => track("Register Clicked")}
          >
            Generate Highlights
          </Link>
          <a
            href="#features"
            className="border border-[#1a1d2e] hover:border-[#2a2d3e] text-gray-300 hover:text-white font-medium px-8 py-3.5 rounded-xl text-base transition-colors text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
            onClick={() => track("Learn More Clicked")}
          >
            Learn More
          </a>
        </div>

        <TrustBadges />
      </div>

      <div className="flex-shrink-0 w-full max-w-sm">
        <HeroCard />
      </div>
    </section>
  );
}

function HeroCard() {
  const highlights = [
    { time: "0:23", label: "Epic clutch", score: 94 },
    { time: "1:47", label: "Kill streak ×5", score: 88 },
    { time: "3:12", label: "Final round", score: 76 },
  ];

  return (
    <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6 shadow-2xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-gray-400 font-mono">session_recording.mp4</span>
        </div>
        <span className="text-xs text-green-400 font-medium">3 highlights</span>
      </div>

      <div className="h-1 bg-[#1a1d2e] rounded-full overflow-hidden mb-5">
        <div className="h-full w-4/5 bg-gradient-to-r from-green-600 to-green-400 rounded-full" />
      </div>

      {highlights.map((h) => (
        <div
          key={h.time}
          className="flex items-center gap-3 py-2.5 border-b border-[#1a1d2e] last:border-0"
        >
          <span className="text-xs text-gray-500 font-mono w-8 flex-shrink-0">{h.time}</span>
          <div className="flex-1 h-1 bg-[#1a1d2e] rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full"
              style={{ width: `${h.score}%` }}
            />
          </div>
          <span className="text-xs text-green-400 font-medium w-6 text-right flex-shrink-0">
            {h.score}
          </span>
          <span className="text-xs text-gray-400 w-24 flex-shrink-0 truncate hidden sm:block">
            {h.label}
          </span>
        </div>
      ))}

      <div className="mt-5 flex items-center justify-between">
        <span className="text-xs text-gray-500">Processing complete</span>
        <span className="text-xs bg-green-500/15 text-green-400 px-2.5 py-1 rounded-full font-medium">
          Ready to export
        </span>
      </div>
    </div>
  );
}

function TrustBadges() {
  const badges = ["AI Powered", "Secure Uploads", "Browser Based", "Public Beta"];

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-3 justify-center md:justify-start">
      {badges.map((label) => (
        <span key={label} className="flex items-center gap-1.5 text-xs text-gray-400">
          <svg
            viewBox="0 0 24 24"
            className="w-3.5 h-3.5 text-green-500 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          {label}
        </span>
      ))}
    </div>
  );
}

// ─── Product Showcase ─────────────────────────────────────────────────────────

function ProductShowcase() {
  return (
    <section id="showcase" className="bg-[#0a0b10] border-y border-[#1a1d2e] py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">Built for Creators</h2>
          <p className="text-gray-400">
            A full-featured dashboard that turns raw footage into ready-to-post content.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-12 items-center">
          <div className="flex-1 w-full min-w-0">
            <DashboardMockup />
          </div>
          <div className="flex-shrink-0 w-full lg:w-72 space-y-7">
            {[
              {
                icon: <IconUpload />,
                title: "Upload Any Format",
                desc: "Drop any video file — MP4, MOV, MKV, AVI, or WebM. Any resolution, any length.",
              },
              {
                icon: <IconBolt />,
                title: "AI Highlight Detection",
                desc: "Frame-by-frame vision analysis combined with audio spike detection scores every moment automatically.",
              },
              {
                icon: <IconServer />,
                title: "Background Processing",
                desc: "Jobs run async. Close the tab and come back when your highlights are ready.",
              },
              {
                icon: <IconPhone />,
                title: "Vertical Reel Output",
                desc: "9:16 clips, auto-thumbnails, and captions — ready for Shorts, TikTok, and Reels.",
              },
            ].map((f) => (
              <div key={f.title} className="flex items-start gap-4">
                <div className="w-9 h-9 bg-green-500/10 rounded-xl flex items-center justify-center text-green-400 flex-shrink-0">
                  {f.icon}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white mb-1">{f.title}</h3>
                  <p className="text-gray-500 text-xs leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function DashboardMockup() {
  return (
    <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl overflow-hidden shadow-2xl">
      {/* Browser chrome */}
      <div className="bg-[#080910] border-b border-[#1a1d2e] px-4 py-3 flex items-center gap-3">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ff5f57]/40" />
          <div className="w-3 h-3 rounded-full bg-[#febc2e]/40" />
          <div className="w-3 h-3 rounded-full bg-[#28c840]/40" />
        </div>
        <div className="flex-1 bg-[#1a1d2e] rounded-md px-3 py-1.5 max-w-xs mx-auto">
          <span className="text-xs text-gray-500 font-mono">vedzovi.com/dashboard</span>
        </div>
      </div>
      {/* App layout */}
      <div className="flex" style={{ minHeight: 320 }}>
        {/* Sidebar */}
        <div className="w-36 border-r border-[#1a1d2e] p-3 flex flex-col gap-1 flex-shrink-0">
          <div className="px-2 py-2 mb-1">
            <span className="text-xs font-bold text-white">Vedzovi</span>
          </div>
          {[
            { label: "Dashboard", active: true },
            { label: "Upload", active: false },
            { label: "Projects", active: false },
            { label: "History", active: false },
          ].map((item) => (
            <div
              key={item.label}
              className={`px-2 py-1.5 rounded-lg text-xs transition-colors ${
                item.active ? "bg-green-500/10 text-green-400 font-medium" : "text-gray-500"
              }`}
            >
              {item.label}
            </div>
          ))}
        </div>
        {/* Main content */}
        <div className="flex-1 p-4 space-y-3 overflow-hidden">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Total Jobs", value: "12" },
              { label: "Clips Ready", value: "8" },
              { label: "Hours Saved", value: "14h" },
            ].map((s) => (
              <div
                key={s.label}
                className="bg-[#080910] border border-[#1a1d2e] rounded-xl p-2.5 text-center"
              >
                <div className="text-base font-bold text-white">{s.value}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>
          {/* Upload panel */}
          <div className="border border-dashed border-[#2a2d3e] rounded-xl p-3 flex items-center gap-3 hover:border-green-600/30 transition-colors">
            <div className="w-8 h-8 bg-green-500/10 rounded-lg flex items-center justify-center text-green-400 flex-shrink-0">
              <IconUploadSm />
            </div>
            <div>
              <div className="text-xs text-white font-medium">Drop video to upload</div>
              <div className="text-xs text-gray-500">MP4, MOV, MKV · Any size</div>
            </div>
          </div>
          {/* Processing job */}
          <div className="bg-[#080910] border border-[#1a1d2e] rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-300 font-medium truncate mr-2">
                session_finals.mp4
              </span>
              <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full flex-shrink-0">
                Processing
              </span>
            </div>
            <div className="h-1 bg-[#1a1d2e] rounded-full overflow-hidden mb-1.5">
              <div className="h-full w-3/5 bg-green-500 rounded-full" />
            </div>
            <div className="text-xs text-gray-500">AI Analysis — 60% complete</div>
          </div>
          {/* Completed job */}
          <div className="bg-[#080910] border border-green-500/20 rounded-xl p-3 flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-300 font-medium">stream_2hr.mp4</div>
              <div className="text-xs text-gray-500 mt-0.5">3 highlights detected</div>
            </div>
            <span className="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-full flex-shrink-0">
              Ready
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Before / After ───────────────────────────────────────────────────────────

function BeforeAfter() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold mb-3">Before &amp; After</h2>
        <p className="text-gray-400">See exactly what Vedzovi transforms your raw footage into.</p>
      </div>

      <div className="flex flex-col md:flex-row items-center gap-4 md:gap-6">
        {/* Before */}
        <div className="flex-1 bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-8 w-full">
          <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center text-red-400 mb-5">
            <IconFilm />
          </div>
          <h3 className="text-lg font-semibold text-white mb-5">Raw Footage</h3>
          <ul className="space-y-3">
            {[
              "2 Hour Full Recording",
              "Large File (10 GB+)",
              "Manual Editing Required",
              "Time Consuming",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-sm text-gray-400">
                <span className="w-4 h-4 rounded-full border border-red-500/30 bg-red-500/10 flex items-center justify-center flex-shrink-0">
                  <svg
                    viewBox="0 0 24 24"
                    className="w-2.5 h-2.5 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Arrow */}
        <div className="flex-shrink-0 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center">
            <svg
              viewBox="0 0 24 24"
              className="w-5 h-5 text-green-400 hidden md:block"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
            <svg
              viewBox="0 0 24 24"
              className="w-5 h-5 text-green-400 md:hidden"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
            </svg>
          </div>
        </div>

        {/* After */}
        <div className="flex-1 bg-[#0d0e14] border border-green-500/20 rounded-2xl p-8 w-full">
          <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center text-green-400 mb-5">
            <IconBolt />
          </div>
          <h3 className="text-lg font-semibold text-white mb-5">Vedzovi Output</h3>
          <ul className="space-y-3">
            {[
              "AI Highlight Reel",
              "Vertical 9:16 Shorts",
              "Auto-Generated Thumbnail",
              "Ready to Upload",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-sm text-gray-400">
                <span className="w-4 h-4 rounded-full border border-green-500/30 bg-green-500/10 flex items-center justify-center flex-shrink-0">
                  <svg
                    viewBox="0 0 24 24"
                    className="w-2.5 h-2.5 text-green-400"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ─────────────────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    {
      number: "01",
      title: "Upload Your Video",
      description:
        "Drop your recording — MP4, MOV, MKV, AVI, or WebM. Any length, any content type.",
    },
    {
      number: "02",
      title: "AI Detects Highlights",
      description:
        "Our pipeline analyzes frames, audio peaks, and action density to find your best moments.",
    },
    {
      number: "03",
      title: "Download Ready-to-Post Reels",
      description:
        "Get vertical highlight clips, thumbnails, and captions — ready for any platform instantly.",
    },
  ];

  return (
    <section id="how-it-works" className="bg-[#0a0b10] border-y border-[#1a1d2e] py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">How It Works</h2>
          <p className="text-gray-400">Three steps from raw footage to viral content.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step, idx) => (
            <div key={step.number} className="relative">
              <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-7 h-full">
                <div className="text-5xl font-bold text-[#1a1d2e] mb-4 font-mono select-none">
                  {step.number}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{step.description}</p>
              </div>
              {idx < steps.length - 1 && (
                <div className="hidden md:flex absolute top-1/2 -right-3 z-10 -translate-y-1/2 w-6 h-6 items-center justify-center bg-[#0a0b10]">
                  <svg
                    viewBox="0 0 24 24"
                    className="w-4 h-4 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── AI Processing Timeline ───────────────────────────────────────────────────

function AITimeline() {
  const steps = [
    {
      icon: <IconUpload />,
      title: "Upload",
      desc: "Drop your video file to start",
    },
    {
      icon: <IconServer />,
      title: "AI Analysis",
      desc: "Frame and audio scanning begins",
    },
    {
      icon: <IconStar />,
      title: "Highlight Detection",
      desc: "Peak moments are scored and ranked",
    },
    {
      icon: <IconPhone />,
      title: "Vertical Reel",
      desc: "9:16 clips are assembled and cropped",
    },
    {
      icon: <IconDownload />,
      title: "Download",
      desc: "Highlights are ready to post",
    },
  ];

  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold mb-3">AI Processing Pipeline</h2>
        <p className="text-gray-400">From raw footage to viral content in five automated steps.</p>
      </div>

      <div className="relative">
        {/* Desktop connector line */}
        <div className="hidden md:block absolute top-8 left-[10%] right-[10%] h-px bg-[#1a1d2e]" />

        <div className="grid grid-cols-1 md:grid-cols-5 gap-0 md:gap-4">
          {steps.map((step, idx) => (
            <div key={step.title} className="flex flex-col items-center text-center">
              {/* Mobile connector */}
              {idx > 0 && (
                <div className="md:hidden flex flex-col items-center mb-4 mt-4">
                  <div className="w-px h-5 bg-[#1a1d2e]" />
                  <svg
                    viewBox="0 0 24 24"
                    className="w-3 h-3 text-[#2a2d3e]"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              )}

              {/* Icon circle */}
              <div className="relative z-10 w-16 h-16 bg-[#0d0e14] border-2 border-[#1a1d2e] rounded-full flex items-center justify-center text-green-400 mb-4">
                {step.icon}
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-green-600 text-white text-xs rounded-full flex items-center justify-center font-bold leading-none">
                  {idx + 1}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-white mb-1.5">{step.title}</h3>
              <p className="text-xs text-gray-500 leading-relaxed max-w-28">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Features ─────────────────────────────────────────────────────────────────

function Features() {
  const items = [
    {
      icon: <IconBolt />,
      title: "AI Highlight Detection",
      description:
        "Frame-by-frame vision analysis combined with audio spike detection to find peak moments automatically.",
    },
    {
      icon: <IconServer />,
      title: "Background Processing",
      description:
        "Jobs run asynchronously so your browser stays responsive. Come back when highlights are ready.",
    },
    {
      icon: <IconPhone />,
      title: "Vertical Reel Generation",
      description:
        "Auto-crops 16:9 footage to 9:16 vertical format, optimized for mobile-first platforms.",
    },
    {
      icon: <IconImage />,
      title: "Automatic Thumbnail Selection",
      description:
        "Picks the highest-impact frame from each highlight as a ready-to-use thumbnail.",
    },
    {
      icon: <IconUsers />,
      title: "Multi-user Dashboard",
      description:
        "Separate accounts, isolated jobs, and personal project history for every user.",
    },
    {
      icon: <IconShield />,
      title: "Secure Cloud Processing",
      description:
        "JWT-authenticated uploads with per-user file isolation. Your footage stays private.",
    },
  ];

  return (
    <section id="features" className="bg-[#0a0b10] border-y border-[#1a1d2e] py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">Everything You Need</h2>
          <p className="text-gray-400">Built for streamers who want results without manual editing.</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item) => (
            <div
              key={item.title}
              className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6 hover:border-[#2a2d3e] transition-colors"
            >
              <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center mb-4 text-green-400">
                {item.icon}
              </div>
              <h3 className="font-semibold text-white mb-2">{item.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Results Section ──────────────────────────────────────────────────────────

function ResultsSection() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold mb-3">Example Outputs</h2>
        <p className="text-gray-400">Vedzovi produces three deliverables for every highlight detected.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Thumbnail card */}
        <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-4 font-semibold">
            Thumbnail Preview
          </div>
          <div
            className="bg-[#080910] border border-[#1a1d2e] rounded-xl overflow-hidden mb-4 relative"
            style={{ aspectRatio: "16/9" }}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-green-900/20 to-transparent" />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center mb-2">
                <IconImage />
              </div>
              <div className="text-xs text-gray-500">Best frame selected</div>
            </div>
            <div className="absolute top-2 right-2 bg-green-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              Score 94
            </div>
          </div>
          <div className="text-sm text-gray-300 font-medium mb-1">High-impact frame</div>
          <div className="text-xs text-gray-500">Auto-selected from peak action moment</div>
        </div>

        {/* Vertical reel card */}
        <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-4 font-semibold">
            Vertical Reel
          </div>
          <div className="flex justify-center mb-4">
            <div
              className="bg-[#080910] border border-[#1a1d2e] rounded-xl overflow-hidden w-28 relative"
              style={{ aspectRatio: "9/16" }}
            >
              <div className="absolute inset-0 bg-gradient-to-b from-green-900/10 to-transparent" />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center mb-1">
                  <IconPhone />
                </div>
                <div className="text-xs text-gray-500">9:16</div>
              </div>
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 w-7 h-7 bg-white/10 rounded-full flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-white" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-300 font-medium mb-1">Mobile-first format</div>
          <div className="text-xs text-gray-500">9:16 crop optimized for all platforms</div>
        </div>

        {/* Metadata card */}
        <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-4 font-semibold">
            Metadata
          </div>
          <div className="space-y-3 mb-4">
            <div>
              <div className="text-xs text-gray-500 mb-1.5">Title</div>
              <div className="bg-[#080910] border border-[#1a1d2e] rounded-lg px-3 py-2 text-xs text-gray-300">
                Epic Clutch Moment — Highlight Reel
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1.5">Hashtags</div>
              <div className="bg-[#080910] border border-[#1a1d2e] rounded-lg px-3 py-2 text-xs text-green-400">
                #highlights #shorts #viral
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1.5">Platform</div>
              <div className="flex gap-1.5 flex-wrap">
                <span className="text-xs border border-red-500/20 bg-red-500/10 text-red-400 rounded-full px-2 py-0.5">
                  YouTube
                </span>
                <span className="text-xs border border-pink-500/20 bg-pink-500/10 text-pink-400 rounded-full px-2 py-0.5">
                  TikTok
                </span>
                <span className="text-xs border border-purple-500/20 bg-purple-500/10 text-purple-400 rounded-full px-2 py-0.5">
                  Reels
                </span>
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-300 font-medium mb-1">Auto-generated metadata</div>
          <div className="text-xs text-gray-500">Title, tags, and platform targeting</div>
        </div>
      </div>
    </section>
  );
}

// ─── Trust Section ────────────────────────────────────────────────────────────

function TrustSection() {
  const items = [
    {
      icon: <IconBolt />,
      title: "AI Powered",
      badge: null,
      desc: "Frame vision analysis and Whisper audio transcription detect highlights automatically.",
    },
    {
      icon: <IconServer />,
      title: "Background Processing",
      badge: null,
      desc: "Async job queue keeps your browser responsive during long AI analysis runs.",
    },
    {
      icon: <IconUsers />,
      title: "Multi-user SaaS",
      badge: null,
      desc: "Isolated accounts, separate job histories, and per-user file storage baked in.",
    },
    {
      icon: <IconShield />,
      title: "Production Ready",
      badge: null,
      desc: "JWT auth, input validation, path protection, and structured logging in place.",
    },
    {
      icon: <IconStar />,
      title: "Public Beta",
      badge: "Free",
      desc: "Open to all users — no credit card required. Help shape the product with your feedback.",
    },
  ];

  return (
    <section className="bg-[#0a0b10] border-y border-[#1a1d2e] py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold mb-3">Built Right</h2>
          <p className="text-gray-400">
            A production-grade platform you can rely on from day one.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item) => (
            <div
              key={item.title}
              className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-6 hover:border-[#2a2d3e] transition-colors"
            >
              <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center mb-4 text-green-400">
                {item.icon}
              </div>
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold text-white">{item.title}</h3>
                {item.badge && (
                  <span className="text-xs bg-green-500/15 text-green-400 px-2 py-0.5 rounded-full font-medium">
                    {item.badge}
                  </span>
                )}
              </div>
              <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Platforms ────────────────────────────────────────────────────────────────

function Platforms() {
  return (
    <section className="bg-[#0a0b10] border-b border-[#1a1d2e] py-16">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-8">
          Export ready for
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <span className="border border-red-500/20 bg-red-500/10 text-red-400 rounded-full px-6 py-2.5 text-sm font-semibold">
            YouTube Shorts
          </span>
          <span className="border border-pink-500/20 bg-pink-500/10 text-pink-400 rounded-full px-6 py-2.5 text-sm font-semibold">
            TikTok
          </span>
          <span className="border border-purple-500/20 bg-purple-500/10 text-purple-400 rounded-full px-6 py-2.5 text-sm font-semibold">
            Instagram Reels
          </span>
        </div>
      </div>
    </section>
  );
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────

function FAQ() {
  const items = [
    {
      q: "What kinds of video are supported?",
      a: "Vedzovi works with any long-form video — gaming, podcasts, sports, meetings, education, vlogs, interviews, and more. It analyzes visual intensity and audio peaks rather than content-specific events, so it supports virtually any format.",
    },
    {
      q: "What is the maximum upload size?",
      a: "There is currently no hard file size cap during beta. Uploads are processed server-side, so very large files (10 GB+) may take longer to transfer. We recommend splitting recordings over 3 hours for the best experience.",
    },
    {
      q: "How long does processing take?",
      a: "Processing time depends on video length and server load. A 1-hour recording typically completes in 10–20 minutes. Jobs run in the background — you can close the tab and return later.",
    },
    {
      q: "Is my footage private?",
      a: "Yes. Uploads are stored under your user account only. No other users can access your files. Your footage is never shared publicly or used for training data.",
    },
    {
      q: "How much does it cost?",
      a: "Vedzovi is free during the public beta. Pricing will be announced before the beta ends. Early users who contribute feedback may receive extended free access.",
    },
    {
      q: "What are the beta limitations?",
      a: "During beta, highlight quality may vary across content types and recording conditions. Processing queues may slow under high server load. Some export formats and platform-specific features are still in active development.",
    },
  ];

  return (
    <section id="faq" className="max-w-6xl mx-auto px-6 py-20">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold mb-3">Frequently Asked</h2>
        <p className="text-gray-400">Answers to common questions about Vedzovi.</p>
      </div>

      <div className="max-w-3xl mx-auto space-y-2">
        {items.map((item) => (
          <details
            key={item.q}
            className="group bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl overflow-hidden"
          >
            <summary className="flex items-center justify-between px-6 py-4 cursor-pointer list-none hover:bg-[#1a1d2e]/40 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500 focus-visible:-outline-offset-2">
              <span className="text-sm font-semibold text-white">{item.q}</span>
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4 text-gray-500 flex-shrink-0 ml-4 transition-transform group-open:rotate-180"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="px-6 pb-5">
              <p className="text-gray-400 text-sm leading-relaxed">{item.a}</p>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

// ─── Beta Notice ──────────────────────────────────────────────────────────────

function BetaNotice() {
  return (
    <section id="beta" className="bg-[#0a0b10] border-y border-[#1a1d2e] py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="bg-gradient-to-br from-[#0d0e14] to-[#0f1020] border border-[#1a1d2e] rounded-2xl p-10 text-center max-w-2xl mx-auto">
          <span className="inline-block bg-green-500/15 text-green-400 text-xs font-semibold uppercase tracking-widest px-3 py-1 rounded-full mb-5">
            Public Beta
          </span>
          <h2 className="text-2xl font-bold mb-3">Help Us Improve</h2>
          <p className="text-gray-400 leading-relaxed mb-8">
            We&apos;re actively improving highlight quality. Your feedback helps shape future AI
            improvements. Beta access is free — no credit card required.
          </p>
          <Link
            href="/register"
            className="bg-green-600 hover:bg-green-700 text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-colors inline-block focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-300"
            onClick={() => track("Register Clicked")}
          >
            Join the Beta
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Final CTA ────────────────────────────────────────────────────────────────

function FinalCTA() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <div className="bg-gradient-to-br from-green-900/20 via-[#0d0e14] to-[#0f1020] border border-green-500/20 rounded-3xl px-8 py-16 md:px-16 md:py-20 text-center">
        <h2 className="text-3xl md:text-5xl font-bold mb-4 leading-tight">
          Ready to Turn Your Videos
          <br />
          <span className="text-green-400">into Viral Shorts?</span>
        </h2>
        <p className="text-gray-400 text-lg mb-10 max-w-xl mx-auto">
          Upload your footage and get AI-generated highlight clips in minutes. No editing skills needed.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/register"
            className="bg-green-600 hover:bg-green-700 text-white font-semibold px-10 py-4 rounded-xl text-base transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-300"
            onClick={() => track("Register Clicked")}
          >
            Start Free Beta
          </Link>
          <Link
            href="/login"
            className="border border-[#2a2d3e] hover:border-[#3a3d4e] text-gray-300 hover:text-white font-medium px-10 py-4 rounded-xl text-base transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
            onClick={() => track("Login Clicked")}
          >
            Login
          </Link>
        </div>
        <p className="text-gray-600 text-xs mt-6">No credit card required. Public beta is free.</p>
      </div>
    </section>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IconBolt() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
      />
    </svg>
  );
}

function IconServer() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3V7.5a3 3 0 013-3h13.5a3 3 0 013 3v3.75a3 3 0 01-3 3m-13.5 0v3.75a3 3 0 003 3h7.5a3 3 0 003-3v-3.75M8.25 9h.008v.008H8.25V9zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
      />
    </svg>
  );
}

function IconPhone() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3"
      />
    </svg>
  );
}

function IconImage() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
      />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
      />
    </svg>
  );
}

function IconShield() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

function IconUploadSm() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

function IconDownload() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
      />
    </svg>
  );
}

function IconStar() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"
      />
    </svg>
  );
}

function IconMenu() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
    </svg>
  );
}

function IconClose() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function IconFilm() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125V6.375m0 13.125A1.125 1.125 0 012.25 18.375M2.25 18.375V6.375m0 0A1.125 1.125 0 013.375 5.25h17.25a1.125 1.125 0 011.125 1.125M21.75 18.375V6.375m0 12A1.125 1.125 0 0120.625 19.5h-1.5c-.621 0-1.125-.504-1.125-1.125m3.75-12A1.125 1.125 0 0020.625 5.25H3.375m0 0h17.25M6 18.375V5.625m12 12.75V5.625M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H13.5m-1.5 3H13.5m-1.5 3H13.5"
      />
    </svg>
  );
}
