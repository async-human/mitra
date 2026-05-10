import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Founder portal · Mitra",
};

/**
 * Smart router for signed-in founders:
 *  - If they already have a job onboarded → redirect to their portal
 *  - Otherwise → show a clear "Set up your portal" page
 */
export default async function FounderSetupPage() {
  const session = await auth();

  if (!session?.user?.email) {
    redirect("/sign-in?role=founder");
  }

  const email = session.user.email;
  const name  = session.user.name?.split(" ")[0] ?? "there";
  const apiBase = process.env.MITRA_API_BASE_URL ?? "http://localhost:8080";

  let portalUrl: string | null = null;
  let lookupError = false;

  try {
    const res = await fetch(
      `${apiBase}/founder/portal-link-by-email?email=${encodeURIComponent(email)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const data = await res.json();
      portalUrl = data.portal_url ?? null;
    }
    // 404 means no job — not an error, just a new founder
  } catch {
    lookupError = true;
  }

  if (portalUrl) {
    redirect(portalUrl);
  }

  // No existing job — show clear setup page instead of silent redirect
  return (
    <main className="fp-setup-page">
      <div className="fp-setup-card">
        <div className="fp-setup-logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <rect width="32" height="32" rx="8" fill="#111" />
            <path d="M8 24V10l8-3 8 3v14l-8 3-8-3Z" stroke="white" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M16 7v17M8 10l8 3 8-3" stroke="white" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
          <span className="fp-setup-brand">Mitra</span>
        </div>

        <h1 className="fp-setup-title">Hi {name}, welcome to Mitra</h1>

        {lookupError ? (
          <p className="fp-setup-sub">
            We couldn&apos;t reach the server right now. Please try again in a moment.
          </p>
        ) : (
          <p className="fp-setup-sub">
            We don&apos;t have an active role posted for <strong>{email}</strong> yet.
            Complete the 2-minute brief and we&apos;ll start sending you matched engineers within 48 hours.
          </p>
        )}

        <div className="fp-setup-actions">
          <Link href="/onboarding" className="fp-setup-btn fp-setup-btn--primary">
            Post your first role →
          </Link>
          {lookupError && (
            <Link href="/founder/setup" className="fp-setup-btn fp-setup-btn--ghost">
              Try again
            </Link>
          )}
        </div>

        <p className="fp-setup-note">
          Already completed onboarding?{" "}
          <a href="mailto:hello@mitra.work" className="fp-setup-link">
            Contact support
          </a>{" "}
          and we&apos;ll reconnect your portal.
        </p>
      </div>
    </main>
  );
}
