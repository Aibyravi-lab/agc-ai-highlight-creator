"use client";

import { Suspense, useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { track } from "../../services/analytics";
import { getSafeLoginRedirect } from "../../utils/loginRedirect";

function LoginContent() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefilledEmail = searchParams.get("email") || "";
  // VED-GROWTH-007: preserves upgrade intent through login — e.g. the
  // pricing page's unauthenticated CTA links here with ?next=/pricing so
  // the user lands back where they expressed intent instead of always on
  // /dashboard. Validated to reject anything but a same-origin relative
  // path (see getSafeLoginRedirect) so this can never become an open redirect.
  const redirectTarget = getSafeLoginRedirect(searchParams.get("next"));

  const [email, setEmail] = useState(prefilledEmail);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && user) {
      router.replace(redirectTarget);
    }
  }, [loading, user, router, redirectTarget]);

  // Arriving here straight from a successful email verification: the
  // email is already known, so send focus straight to the password field.
  useEffect(() => {
    if (prefilledEmail && !loading && !user) {
      passwordRef.current?.focus();
    }
  }, [prefilledEmail, loading, user]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      track("User Logged In");
      track("Login Success");
      router.replace(redirectTarget);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#08090d] flex items-center justify-center">
        <div className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#08090d] flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white tracking-tight">Vedzovi</h1>
          <p className="text-gray-500 text-sm mt-1">AI Video Intelligence</p>
        </div>

        {/* Card */}
        <div className="bg-[#0d0e14] border border-[#1a1d2e] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-1">Sign in</h2>
          <p className="text-gray-500 text-sm mb-6">
            Welcome back. Enter your credentials to continue.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#08090d] border border-[#1a1d2e] text-white text-sm placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm text-gray-400" htmlFor="password">
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-sm text-green-400 hover:text-green-300 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                ref={passwordRef}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#08090d] border border-[#1a1d2e] text-white text-sm placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3.5 py-2.5">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        {/* Footer link */}
        <p className="text-center text-sm text-gray-500 mt-5">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}
