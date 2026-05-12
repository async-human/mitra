import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "@/components/Logo";
import { WhatsAppIcon } from "@/components/icons";
import type { Metadata } from "next";

import { MatchesPanelClient } from "./MatchesPanelClient";
import { IntrosPanelClient } from "./IntrosPanelClient";
import { UserMenu } from "./UserMenu";
import { JourneyStrip } from "./JourneyStrip";

function ChatIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
      <path d="M14.5 9.5a6 6 0 0 1-8.5 5.4L2 16l1.1-4A6 6 0 1 1 14.5 9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export const metadata: Metadata = {
  title: "Dashboard · Mitra",
};

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
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
          <UserMenu name={user.name} email={user.email} image={user.image} />
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
        <JourneyStrip userEmail={user.email ?? ""} />

        {/* Primary CTA */}
        <section className="dash-cta-section">
          <div className="dash-cta-card">
            <div className="dash-cta-text">
              <h2 className="dash-cta-title">Ready to start?</h2>
              <p className="dash-cta-sub">
                Chat with Mitra right here — tell us what you&apos;re looking for. Takes 2 minutes. No CV needed.
              </p>
            </div>
            <div className="dash-cta-btns">
              <Link href="/chat" className="dash-wa-btn">
                <ChatIcon />
                Chat with Mitra
              </Link>
              <a href={waHref} target="_blank" rel="noopener noreferrer" className="dash-wa-btn dash-wa-btn--secondary">
                <WhatsAppIcon size={17} />
                Open in WhatsApp
              </a>
            </div>
          </div>
          <p className="dash-cta-note">Free for candidates · Always</p>
        </section>

        {/* Panels */}
        <section className="dash-panels">
          <div className="dash-panel">
            <MatchesPanelClient userEmail={user.email ?? ""} />
          </div>

          <div className="dash-panel">
            <IntrosPanelClient userEmail={user.email ?? ""} />
          </div>
        </section>

      </main>

      <footer className="dash-footer">
        <p>Mitra keeps your data private. <Link href="/cookies" className="dash-footer-link">Privacy policy</Link></p>
      </footer>
    </div>
  );
}
