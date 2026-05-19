import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { UserMenu } from "@/app/dashboard/UserMenu";

export const metadata: Metadata = {
  title: "Founder portal · Mitra",
};

interface FounderJob {
  job_id: number;
  title: string;
  company: string;
  stage: string | null;
  portal_url: string;
  total_intros: number;
  to_review: number;
}

function companyInitials(company: string): string {
  const words = company.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return company.slice(0, 2).toUpperCase();
}

/**
 * Smart router for signed-in founders:
 *  - 0 jobs  → show "Post your first role" page
 *  - 1 job   → redirect directly to that portal
 *  - 2+ jobs → show a role picker so the founder chooses which to manage
 */
export default async function FounderSetupPage({
  searchParams,
}: {
  searchParams: Promise<{ list?: string }>;
}) {
  const params = await searchParams;
  const forceList = params.list === "1";

  const session = await auth();

  if (!session?.user?.email) {
    redirect("/sign-in?role=founder");
  }

  const email = session.user.email;
  const name  = session.user.name?.split(" ")[0] ?? "there";
  const apiBase = (
    process.env.MITRA_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8080"
  ).replace(/\/$/, "");

  let jobs: FounderJob[] = [];
  let lookupError = false;

  try {
    // Try the multi-role endpoint first (requires latest backend)
    const res = await fetch(
      `${apiBase}/founder/all-portals-by-email?email=${encodeURIComponent(email)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const data = await res.json();
      jobs = data.jobs ?? [];
    } else {
      // Endpoint doesn't exist yet on this backend version — fall back to single-job lookup
      const fallback = await fetch(
        `${apiBase}/founder/portal-link-by-email?email=${encodeURIComponent(email)}`,
        { cache: "no-store" },
      );
      if (fallback.ok) {
        const d = await fallback.json();
        if (d.portal_url) {
          jobs = [{ job_id: d.job_id ?? 0, title: "Your role", company: "", stage: null, portal_url: d.portal_url, total_intros: 0, to_review: 0 }];
        }
      }
    }
  } catch {
    lookupError = true;
  }

  // Zero jobs + no error — go straight to onboarding (company form lives there).
  // On API errors, stay on this page so the founder can retry instead of being sent to onboarding.
  if (jobs.length === 0 && !lookupError) {
    redirect("/onboarding");
  }

  // Single job — redirect to dashboard (which shows the role)
  if (jobs.length === 1 && !forceList) {
    redirect('/founder/dashboard');
  }

  const setupUserMenu = (
    <UserMenu
      name={session.user.name}
      email={session.user.email}
      image={session.user.image}
    />
  );

  // Multiple jobs OR forced list view — show role picker
  if (jobs.length > 1 || (jobs.length === 1 && forceList)) {
    return (
      <main className="fp-setup-page">
        <header className="fp-setup-topbar">
          <Link href="/" className="fp-setup-topbar-brand">
            Mitra<span className="fp-setup-topbar-brand-dot">.</span>
          </Link>
          {setupUserMenu}
        </header>
        <div className="fp-setup-page-body">
        <div className="fp-setup-card fp-setup-card--wide">
          <div className="fp-setup-logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="#111" />
              <path d="M8 24V10l8-3 8 3v14l-8 3-8-3Z" stroke="white" strokeWidth="1.5" strokeLinejoin="round" />
              <path d="M16 7v17M8 10l8 3 8-3" stroke="white" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
            <span className="fp-setup-brand">Mitra</span>
          </div>

          <div>
            <h1 className="fp-setup-title">Your open roles</h1>
            <p className="fp-setup-sub" style={{ marginTop: 6 }}>
              Select a role to review candidates and manage introductions.
            </p>
          </div>

          {/* Role cards */}
          <div className="fp-setup-roles">
            {jobs.map((job) => (
              <a key={job.job_id} href={job.portal_url} className="fp-setup-role-card">
                <div className="fp-setup-role-avatar">
                  {companyInitials(job.company)}
                </div>
                <div className="fp-setup-role-info">
                  <p className="fp-setup-role-title">{job.title}</p>
                  <p className="fp-setup-role-company">{job.company}</p>
                </div>

                <div className="fp-setup-role-meta">
                  {job.to_review > 0 ? (
                    <span className="fp-setup-role-badge fp-setup-role-badge--action">
                      {job.to_review} to review
                    </span>
                  ) : job.total_intros > 0 ? (
                    <span className="fp-setup-role-badge fp-setup-role-badge--neutral">
                      {job.total_intros} introduced
                    </span>
                  ) : job.stage ? (
                    <span className="fp-setup-role-badge">{job.stage}</span>
                  ) : null}
                </div>

                <svg className="fp-setup-role-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            ))}
          </div>

          {/* Add another role */}
          <div className="fp-setup-divider">or</div>
          <Link href="/onboarding" className="fp-setup-btn fp-setup-btn--ghost">
            + Post another role
          </Link>

          <p className="fp-setup-note">
            Signed in as <strong style={{ fontWeight: 500 }}>{email}</strong>
          </p>
        </div>
        </div>
      </main>
    );
  }

  // Zero jobs — show onboarding CTA
  return (
    <main className="fp-setup-page">
      <header className="fp-setup-topbar">
        <Link href="/" className="fp-setup-topbar-brand">
          Mitra<span className="fp-setup-topbar-brand-dot">.</span>
        </Link>
        {setupUserMenu}
      </header>
      <div className="fp-setup-page-body">
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
            We don&apos;t have an active role posted for{" "}
            <strong>{email}</strong> yet. Complete the 2-minute brief and
            we&apos;ll start sending you matched engineers within 48 hours.
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
          Need help?{" "}
          <a href="mailto:hello@mitra.work" className="fp-setup-link">
            Contact support
          </a>
        </p>
      </div>
      </div>
    </main>
  );
}
