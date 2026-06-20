"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, LockKeyhole, LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const DEMO_USERS = ["admin", "operator", "auditor", "viewer"];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("operator");
  const [password, setPassword] = useState("UrbanShield123!");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-50 lg:grid-cols-[minmax(0,0.95fr)_minmax(420px,0.55fr)]">
      <section className="flex min-h-[46vh] flex-col justify-between bg-ink p-6 text-white sm:p-10 lg:min-h-screen">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-md bg-teal-500">
            <Building2 className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-normal">UrbanShield</h1>
            <p className="text-sm text-white/62">Operations console</p>
          </div>
        </div>
        <div className="max-w-2xl">
          <ShieldCheck className="mb-5 h-10 w-10 text-teal-300" />
          <h2 className="max-w-xl text-4xl font-bold leading-tight tracking-normal sm:text-5xl">
            Secure local command for incidents, dispatch, simulations, and audit.
          </h2>
          <p className="mt-4 max-w-lg text-base leading-7 text-white/68">
            Sign in with one of the seeded local roles to exercise role-aware workflows without external identity services.
          </p>
        </div>
        <p className="text-xs text-white/46">Development credentials are seeded locally and must not be reused in production.</p>
      </section>

      <section className="flex items-center justify-center p-5 sm:p-8">
        <form onSubmit={handleSubmit} className="w-full max-w-md rounded-lg border border-line bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="rounded-md bg-teal-50 p-2 text-teal-700">
              <LockKeyhole className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-xl font-bold text-ink">Sign In</h2>
              <p className="text-sm text-muted">Local role-based access</p>
            </div>
          </div>

          <div className="space-y-4">
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Role Account
              <select
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="rounded-md border border-line bg-white px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              >
                {DEMO_USERS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
          </div>

          {error && (
            <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-teal-700 disabled:opacity-60"
          >
            <LogIn className="h-4 w-4" />
            {submitting ? "Signing in..." : "Enter Console"}
          </button>
        </form>
      </section>
    </main>
  );
}
