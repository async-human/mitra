"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import s from "./WhatsAppGate.module.css";

function PhoneIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="9" y="2" width="14" height="22" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="16" cy="20.5" r="1.2" fill="currentColor" />
      <path d="M13 5.5h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ClockBadge() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="8" fill="#e87840" />
      <path d="M9 5v4l2.5 2" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function WhatsAppGate() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    function intercept(e: MouseEvent) {
      const anchor = (e.target as Element).closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href") ?? "";
      if (href.includes("wa.me") || href.includes("whatsapp.com")) {
        e.preventDefault();
        e.stopPropagation();
        setOpen(true);
      }
    }

    document.addEventListener("click", intercept, true);
    return () => document.removeEventListener("click", intercept, true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!mounted || !open) return null;

  return createPortal(
    <div
      className={s.overlay}
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-labelledby="wa-gate-title"
    >
      <div className={s.modal} onClick={e => e.stopPropagation()}>
        <button
          className={s.close}
          onClick={() => setOpen(false)}
          aria-label="Close"
        >
          ×
        </button>

        <div className={s.iconWrap}>
          <PhoneIcon />
          <span className={s.badge}><ClockBadge /></span>
        </div>

        <h2 id="wa-gate-title" className={s.title}>
          Almost embarrassingly close.
        </h2>

        <p className={s.body}>
          The matching engine is live, the roles are queued, and the
          intros are staged. WhatsApp intake is the last piece we&apos;re
          wiring up — our engineer is in a meeting about it right now.{" "}
          <span className={s.aside}>(We see the irony.)</span>
        </p>

        <p className={s.body}>
          Sign in and we&apos;ll notify you the moment the line opens.
          First message is yours.
        </p>

        <div className={s.actions}>
          <Link
            href="/sign-in"
            className={s.btnPrimary}
            onClick={() => setOpen(false)}
          >
            Sign in — it&apos;s free
          </Link>
          <button className={s.btnGhost} onClick={() => setOpen(false)}>
            I&apos;ll check back later
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
