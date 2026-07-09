"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "../../services/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
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
          <h2 className="text-lg font-semibold text-white mb-1">Forgot password</h2>
          <p className="text-gray-500 text-sm mb-6">
            Enter your email and we&apos;ll send you a link to reset your password.
          </p>

          {submitted ? (
            <p className="text-green-400 text-sm bg-green-500/10 border border-green-500/20 rounded-lg px-3.5 py-2.5">
              If an account exists for that email, a password reset link has
              been sent.
            </p>
          ) : (
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
                {submitting ? "Sending…" : "Send reset link"}
              </button>
            </form>
          )}
        </div>

        {/* Footer link */}
        <p className="text-center text-sm text-gray-500 mt-5">
          Remembered your password?{" "}
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
