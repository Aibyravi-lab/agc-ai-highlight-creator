"use client";

import Link from "next/link";

interface ErrorFallbackProps {
  reset: () => void;
}

export function ErrorFallback({ reset }: ErrorFallbackProps) {
  return (
    <div className="min-h-screen bg-[#08090d] text-white flex items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <div className="text-lg font-bold tracking-tight mb-6">Vedzovi</div>

        <h1 className="text-2xl font-bold mb-3">Something went wrong</h1>
        <p className="text-gray-400 text-sm mb-8">
          We hit an unexpected error while processing that. Your data is safe
          — try again, or head back and pick up where you left off.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => reset()}
            className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-6 rounded-lg text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
          >
            Retry
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto bg-transparent border border-[#1a1d2e] hover:border-green-500/60 text-white font-medium py-2.5 px-6 rounded-lg text-sm text-center transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
