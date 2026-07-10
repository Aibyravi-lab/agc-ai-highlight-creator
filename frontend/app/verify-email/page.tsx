"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { verifyEmail } from "../../services/auth";

type VerifyState = "loading" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [state, setState] = useState<VerifyState>(
    token ? "loading" : "error"
  );
  const [message, setMessage] = useState(
    token ? "" : "This verification link is missing or invalid."
  );

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    verifyEmail(token)
      .then((res) => {
        if (cancelled) return;
        setMessage(res.message);
        setState("success");
      })
      .catch((err) => {
        if (cancelled) return;
        setMessage(err instanceof Error ? err.message : "Verification failed");
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="min-h-screen bg-[#08090d] flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white tracking-tight">Vedzovi</h1>
          <p className="text-gray-500 text-sm mt-1">AI Video Intelligence</p>
        </div>

        {/* Card */}
        <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-8 text-center">
          {state === "loading" && (
            <>
              <div className="w-6 h-6 mx-auto mb-4 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
              <p className="text-gray-400 text-sm">Verifying your email…</p>
            </>
          )}

          {state === "success" && (
            <>
              <h2 className="text-lg font-semibold text-white mb-2">Email verified</h2>
              <p className="text-green-400 text-sm bg-green-500/10 border border-green-500/20 rounded-lg px-3.5 py-2.5 mb-6">
                {message || "Your email has been verified successfully."}
              </p>
              <Link
                href="/login"
                className="block w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
              >
                Sign in
              </Link>
            </>
          )}

          {state === "error" && (
            <>
              <h2 className="text-lg font-semibold text-white mb-2">Verification failed</h2>
              <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3.5 py-2.5 mb-6">
                {message || "This verification link is invalid or has expired."}
              </p>
              <Link
                href="/login"
                className="block w-full bg-[#1a1d2e] hover:bg-[#232640] text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
              >
                Back to sign in
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
