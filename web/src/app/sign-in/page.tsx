import { signIn } from "@/auth";
import { Logo } from "@/components/Logo";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in · Mitra",
  description: "Sign in to Mitra — your personal AI talent agent.",
};

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4" />
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853" />
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05" />
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <rect width="18" height="18" rx="3" fill="#0A66C2" />
      <path d="M4.5 7H6.5V13.5H4.5V7ZM5.5 6C4.948 6 4.5 5.552 4.5 5C4.5 4.448 4.948 4 5.5 4C6.052 4 6.5 4.448 6.5 5C6.5 5.552 6.052 6 5.5 6Z" fill="white" />
      <path d="M8 7H9.9V7.9C10.2 7.3 11 6.8 12.1 6.8C14 6.8 14.5 7.9 14.5 9.5V13.5H12.5V10C12.5 9.2 12.5 8.2 11.4 8.2C10.3 8.2 10 9 10 9.9V13.5H8V7Z" fill="white" />
    </svg>
  );
}

function CandidateIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="14" cy="10" r="5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M4 24c0-5.523 4.477-10 10-10s10 4.477 10 10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function FounderIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect x="3" y="8" width="22" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M9 8V6a5 5 0 0 1 10 0v2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M3 15h22" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="14" cy="15" r="2.5" fill="currentColor" />
    </svg>
  );
}

type Props = { searchParams: { role?: string; callbackUrl?: string } };

export default function SignInPage({ searchParams }: Props) {
  const role = searchParams.role as "candidate" | "founder" | undefined;
  const redirectTo = role === "founder" ? "/founder/setup" : "/dashboard";

  // ── No role selected: show role picker ──────────────────────────────────────
  if (!role) {
    return (
      <main className="signin-page">
        <div className="signin-glow signin-glow--a" aria-hidden="true" />
        <div className="signin-glow signin-glow--b" aria-hidden="true" />

        <div className="signin-card signin-card--wide">
          <div className="signin-logo-row"><Logo /></div>

          <div className="signin-header">
            <h1 className="signin-title">Welcome to Mitra</h1>
            <p className="signin-sub">Who are you signing in as?</p>
          </div>

          <div className="signin-role-grid">
            <Link href="/sign-in?role=candidate" className="signin-role-card">
              <div className="signin-role-icon signin-role-icon--candidate">
                <CandidateIcon />
              </div>
              <div className="signin-role-text">
                <span className="signin-role-title">I&apos;m a candidate</span>
                <span className="signin-role-desc">Looking for my next engineering role</span>
              </div>
              <span className="signin-role-arrow">→</span>
            </Link>

            <Link href="/sign-in?role=founder" className="signin-role-card">
              <div className="signin-role-icon signin-role-icon--founder">
                <FounderIcon />
              </div>
              <div className="signin-role-text">
                <span className="signin-role-title">I&apos;m a founder</span>
                <span className="signin-role-desc">Looking to hire great engineers</span>
              </div>
              <span className="signin-role-arrow">→</span>
            </Link>
          </div>

          <p className="signin-fine">
            By signing in you agree to Mitra&apos;s{" "}
            <a href="/cookies" className="signin-fine-link">Privacy Policy</a>
            {" "}and{" "}
            <a href="#" className="signin-fine-link">Terms of Service</a>.
          </p>
        </div>
      </main>
    );
  }

  // ── Role selected: show provider buttons ────────────────────────────────────
  const isFounder = role === "founder";

  return (
    <main className="signin-page">
      <div className="signin-glow signin-glow--a" aria-hidden="true" />
      <div className="signin-glow signin-glow--b" aria-hidden="true" />

      <div className="signin-card">
        <div className="signin-logo-row"><Logo /></div>

        {/* Role badge */}
        <div className="signin-role-badge-row">
          <span className={`signin-role-badge signin-role-badge--${role}`}>
            {isFounder ? <FounderIcon /> : <CandidateIcon />}
            {isFounder ? "Signing in as founder" : "Signing in as candidate"}
          </span>
          <Link href="/sign-in" className="signin-role-change">Change</Link>
        </div>

        <div className="signin-header">
          <h1 className="signin-title">
            {isFounder ? "Founder portal" : "Welcome back"}
          </h1>
          <p className="signin-sub">
            {isFounder
              ? "Sign in to review candidates and manage introductions."
              : "Sign in to track your pipeline and pick up where you left off."}
          </p>
        </div>

        <div className="signin-providers">
          <form
            action={async () => {
              "use server";
              await signIn("google", { redirectTo });
            }}
          >
            <button type="submit" className="signin-btn signin-btn--google">
              <GoogleIcon />
              Continue with Google
            </button>
          </form>

          <div className="signin-divider">
            <span /><p>or</p><span />
          </div>

          <form
            action={async () => {
              "use server";
              await signIn("linkedin", { redirectTo });
            }}
          >
            <button type="submit" className="signin-btn signin-btn--linkedin">
              <LinkedInIcon />
              Continue with LinkedIn
            </button>
          </form>
        </div>

        <p className="signin-fine">
          By signing in you agree to Mitra&apos;s{" "}
          <a href="/cookies" className="signin-fine-link">Privacy Policy</a>
          {" "}and{" "}
          <a href="#" className="signin-fine-link">Terms of Service</a>.
        </p>
      </div>
    </main>
  );
}
