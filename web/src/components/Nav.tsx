"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { WhatsAppIcon } from "./icons";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`nav${scrolled ? " scrolled" : ""}`} aria-label="Primary">
      <Logo />
      <ul className="nav-mid">
        <li>
          <Link href="#how">How it works</Link>
        </li>
        <li>
          <Link href="#fit">Who it&apos;s for</Link>
        </li>
        <li>
          <Link href="#founders">Warm intros</Link>
        </li>
        <li>
          <Link href="#stories">Stories</Link>
        </li>
        <li>
          <Link href="#pricing">Pricing</Link>
        </li>
      </ul>
      <div className="nav-end">
        <ThemeToggle />
        <Link href="/sign-in" className="btn-ghost">
          Sign in
        </Link>
        <a
          href={whatsAppHrefFor("general")}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-amber"
        >
          <WhatsAppIcon size={14} />
          Chat with Mitra
        </a>
      </div>
    </nav>
  );
}
