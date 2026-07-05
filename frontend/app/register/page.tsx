"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { track } from "../../services/analytics";

export default function RegisterPage() {
  const { register, user, loading } = useAuth();
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter your password.");
      return;
    }

    if (!agreedToTerms) {
      setError("Please agree to the Privacy Policy and Terms & Conditions to continue.");
      return;
    }

    setSubmitting(true);
    try {
      await register(name, email, password);
      track("User Registered");
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
          <h2 className="text-lg font-semibold text-white mb-1">Create account</h2>
          <p className="text-gray-500 text-sm mb-6">
            Start generating AI highlights from your videos.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5" htmlFor="name">
                Name
              </label>
              <input
                id="name"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#08090d] border border-[#1a1d2e] text-white text-sm placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors"
                placeholder="Your name"
              />
            </div>

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
              <label className="block text-sm text-gray-400 mb-1.5" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#08090d] border border-[#1a1d2e] text-white text-sm placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors"
                placeholder="Min. 8 characters"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5" htmlFor="confirm-password">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#08090d] border border-[#1a1d2e] text-white text-sm placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors"
                placeholder="Re-enter your password"
              />
            </div>

            <div className="flex items-start gap-2.5">
              <input
                id="agree-terms"
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-[#1a1d2e] bg-[#08090d] accent-green-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-500"
              />
              <label htmlFor="agree-terms" className="text-sm text-gray-400 leading-snug">
                I agree to the{" "}
                <Link
                  href="/privacy"
                  className="text-green-400 hover:text-green-300 transition-colors"
                >
                  Privacy Policy
                </Link>{" "}
                and{" "}
                <Link
                  href="/terms"
                  className="text-green-400 hover:text-green-300 transition-colors"
                >
                  Terms &amp; Conditions
                </Link>
                .
              </label>
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
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
        </div>

        {/* Footer link */}
        <p className="text-center text-sm text-gray-500 mt-5">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-green-400 hover:text-green-300 transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
