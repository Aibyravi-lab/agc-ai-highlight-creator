import type { AuthUser, AuthResult, RegisterResult } from "../types/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "";

async function authRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    cache: "no-store",
    ...options,
  });

  if (!res.ok) {
    let message = "Request failed.";
    const text = await res.text().catch(() => "");
    if (text) {
      try {
        const err = JSON.parse(text);
        message = err.detail || err.message || JSON.stringify(err);
      } catch {
        message = text;
      }
    }
    throw new Error(message);
  }

  return res.json();
}

export async function login(
  email: string,
  password: string
): Promise<AuthResult> {
  const data = await authRequest<{
    access_token: string;
    user: AuthUser;
  }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  return { token: data.access_token, user: data.user };
}

export async function register(
  name: string,
  email: string,
  password: string
): Promise<RegisterResult> {
  // AGC-070: registration no longer returns an access_token — the account
  // is created unverified and a verification email is sent. No session is
  // established here.
  const data = await authRequest<{
    message: string;
    user: AuthUser;
  }>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  return { message: data.message, user: data.user };
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  const data = await authRequest<{ user: AuthUser }>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return data.user;
}

export function logout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("agc_token");
  }
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const data = await authRequest<{ message: string }>("/auth/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  return { message: data.message };
}

export async function resetPassword(
  token: string,
  newPassword: string
): Promise<{ message: string }> {
  const data = await authRequest<{ message: string }>("/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });

  return { message: data.message };
}

export async function verifyEmail(
  token: string
): Promise<{ message: string; email?: string }> {
  // AGC-070: verification intentionally does not return an access_token —
  // possession of the (single-use, but still URL-embedded) verification
  // link must not be enough to authenticate. `email` is not a secret (it's
  // the address the caller just proved they control) and is only used to
  // pre-fill the sign-in form.
  const data = await authRequest<{ message: string; email?: string }>(
    "/auth/verify-email",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    }
  );

  return { message: data.message, email: data.email };
}
