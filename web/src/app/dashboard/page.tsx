import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "@/components/Logo";
import { WhatsAppIcon } from "@/components/icons";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard · Mitra",
};

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <rect x="2" y="6" width="9" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4 6V4.5a2.5 2.5 0 1 1 5 0V6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function MatchesEmptyIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect x="4" y="10" width="32" height="22" rx="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 16h32" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="11" cy="13" r="1.5" fill="currentColor" />
      <circle cx="16" cy="13" r="1.5" fill="currentColor" />
      <path d="M12 24h8M12 28h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function IntrosEmptyIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path d="M6 10h28a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 12l16 11 16-11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) redirect("/sign-in");

  const user = session.user;
  const firstName = user.name?.split(" ")[0] ?? "there";
  const greeting = getGreeting();
  const waHref = whatsAppHrefFor("candidate");

  return (
    <div className="dash-root">

      {/* ── Top bar ── */}
      <header className="dash-topbar">
        <Logo />
        <div className="dash-topbar-right">
          <Link href="/" className="dash-topbar-back">← Back to site</Link>
          <div className="dash-topbar-user">
            {user.image ? (
              <img src={user.image} alt={user.name ?? ""} className="dash-topbar-av" referrerPolicy="no-referrer" />
            ) : (
              <span className="dash-topbar-av dash-topbar-av--fallback">{user.name?.[0] ?? "U"}</span>
            )}
            <span className="dash-topbar-name">{user.name}</span>
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="dash-main">

        {/* Greeting */}
        <section className="dash-greeting">
          <p className="dash-greeting-eyebrow">{greeting}</p>
          <h1 className="dash-greeting-h1">{firstName}.</h1>
          <p className="dash-greeting-sub">
            Your next move starts with one honest conversation.
          </p>
        </section>

        {/* Journey strip */}
        <section className="dash-journey">
          <div className="dash-journey-inner">

            <div className="dash-step dash-step--done">
              <div className="dash-step-icon dash-step-icon--done"><CheckIcon /></div>
              <div className="dash-step-body">
                <div className="dash-step-label">Step 1</div>
                <div className="dash-step-title">Signed in</div>
                <div className="dash-step-desc">You&apos;re here. That&apos;s the start.</div>
              </div>
            </div>

            <div className="dash-step-line" />

            <div className="dash-step dash-step--current">
              <div className="dash-step-icon dash-step-icon--current">
                <WhatsAppIcon size={16} />
              </div>
              <div className="dash-step-body">
                <div className="dash-step-label">Step 2 — Now</div>
                <div className="dash-step-title">Chat with Mitra</div>
                <div className="dash-step-desc">
                  A 2-minute WhatsApp conversation — your experience, what you want, what you won&apos;t compromise on.
                </div>
              </div>
            </div>

            <div className="dash-step-line" />

            <div className="dash-step dash-step--locked">
              <div className="dash-step-icon dash-step-icon--locked"><LockIcon /></div>
              <div className="dash-step-body">
                <div className="dash-step-label">Step 3</div>
                <div className="dash-step-title">Receive your matches</div>
                <div className="dash-step-desc">
                  3–5 curated introductions, each with a clear reason why. No ghosting, ever.
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* Primary CTA */}
        <section className="dash-cta-section">
          <div className="dash-cta-card">
            <div className="dash-cta-text">
              <h2 className="dash-cta-title">Ready to start?</h2>
              <p className="dash-cta-sub">
                Open WhatsApp and tell Mitra what you&apos;re looking for. Takes 2 minutes. No CV needed.
              </p>
            </div>
            <a href={waHref} target="_blank" rel="noopener noreferrer" className="dash-wa-btn">
              <WhatsAppIcon size={17} />
              Start on WhatsApp
            </a>
          </div>
          <p className="dash-cta-note">Free for candidates · Always</p>
        </section>

        {/* Empty state cards */}
        <section className="dash-panels">
          <div className="dash-panel">
            <div className="dash-panel-head">
              <h3 className="dash-panel-title">Your matches</h3>
              <span className="dash-panel-badge">0 active</span>
            </div>
            <div className="dash-empty">
              <div className="dash-empty-icon"><MatchesEmptyIcon /></div>
              <p className="dash-empty-title">No matches yet</p>
              <p className="dash-empty-desc">
                Complete your WhatsApp conversation and we&apos;ll surface the roles built for someone like you.
              </p>
              <a href={waHref} target="_blank" rel="noopener noreferrer" className="dash-empty-cta">
                Start the conversation →
              </a>
            </div>
          </div>

          <div className="dash-panel">
            <div className="dash-panel-head">
              <h3 className="dash-panel-title">Introductions</h3>
              <span className="dash-panel-badge">0 sent</span>
            </div>
            <div className="dash-empty">
              <div className="dash-empty-icon"><IntrosEmptyIcon /></div>
              <p className="dash-empty-title">No intros yet</p>
              <p className="dash-empty-desc">
                Once your matches are confirmed, we send a warm introduction to the founder on your behalf.
              </p>
              <p className="dash-empty-cta dash-empty-cta--muted">Available after matching</p>
            </div>
          </div>
        </section>

      </main>

      <footer className="dash-footer">
        <p>Mitra keeps your data private. <Link href="/cookies" className="dash-footer-link">Privacy policy</Link></p>
      </footer>
    </div>
  );
}
