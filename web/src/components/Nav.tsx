"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { WhatsAppIcon } from "./icons";
import { useAudience } from "./AudienceContext";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [pastHero, setPastHero] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { audience, setAudience } = useAudience();
  const { data: session } = useSession();

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 60);
      setPastHero(window.scrollY > window.innerHeight * 0.75);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`nav${scrolled ? " scrolled" : ""}`} aria-label="Primary">
      <Logo />
      <ul className="nav-mid">
        <li><Link href="#how">How it works</Link></li>
        <li><Link href="#fit">Who it&apos;s for</Link></li>
        <li><Link href="#founders">Warm intros</Link></li>
        <li><Link href="#pricing">Pricing</Link></li>
      </ul>
      <div className="nav-end">
        {pastHero && (
          <div className="nav-aud-tog" role="group" aria-label="I am a">
            <button
              type="button"
              className={`nav-aud-btn${audience === "candidate" ? " on" : ""}`}
              onClick={() => setAudience("candidate")}
            >
              Looking for a role
            </button>
            <button
              type="button"
              className={`nav-aud-btn${audience === "founder" ? " on" : ""}`}
              onClick={() => setAudience("founder")}
            >
              Hiring
            </button>
          </div>
        )}
        <ThemeToggle />
        {session?.user ? (
          <div className="nav-user" onMouseLeave={() => setUserMenuOpen(false)}>
            <button
              className="nav-user-btn"
              onClick={() => setUserMenuOpen((o) => !o)}
              aria-label="User menu"
            >
              {session.user.image ? (
                <img src={session.user.image} alt="" className="nav-user-av" referrerPolicy="no-referrer" />
              ) : (
                <span className="nav-user-av nav-user-av--fallback">
                  {session.user.name?.[0] ?? "U"}
                </span>
              )}
            </button>
            {userMenuOpen && (
              <div className="nav-user-menu">
                <div className="nav-user-menu-name">{session.user.name}</div>
                <div className="nav-user-menu-email">{session.user.email}</div>
                <hr className="nav-user-menu-sep" />
                <button
                  className="nav-user-menu-item nav-user-menu-item--danger"
                  onClick={() => signOut({ callbackUrl: "/" })}
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <Link
            href={audience === "founder" ? "/sign-in?role=founder" : "/sign-in?role=candidate"}
            className="btn-ghost"
          >
            Sign in
          </Link>
        )}
        <a
          href={whatsAppHrefFor(audience === "founder" ? "founder" : "candidate")}
          target="_blank"
          rel="noopener noreferrer"
          className={`btn-amber${audience === "founder" ? " btn-amber--teal" : ""}`}
        >
          <WhatsAppIcon size={14} />
          {audience === "founder" ? "List a role" : "Chat with Mitra"}
        </a>
      </div>
    </nav>
  );
}
