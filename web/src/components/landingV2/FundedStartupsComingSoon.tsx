"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import s from "./landing-v2.module.css";

const MODAL_FEATURES = [
  "Recently funded companies across fintech, SaaS, and consumer",
  "Stage, sector, and round details in one place",
  "Roles you can get warm-introduced to via Mitra",
] as const;

type TriggerVariant = "nav" | "footer" | "hero";

const FundedStartupsCtx = createContext<{ open: () => void } | null>(null);

function useFundedStartupsComingSoon() {
  const ctx = useContext(FundedStartupsCtx);
  if (!ctx) {
    throw new Error("FundedStartupsTrigger must be used within FundedStartupsComingSoonProvider");
  }
  return ctx;
}

function ComingSoonModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const titleId = useId();
  const descId = useId();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || !mounted) return null;

  return createPortal(
    <div
      className={s.csOverlay}
      onClick={onClose}
      role="presentation"
    >
      <div
        className={s.csModal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={s.csModalAccent} aria-hidden="true" />

        <button type="button" className={s.csClose} onClick={onClose} aria-label="Close">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>

        <div className={s.csModalContent}>
          <p className={s.csModalEyebrow}>
            <span className={s.csModalEyebrowDot} />
            Coming soon
          </p>

          <h2 id={titleId} className={s.csModalTitle}>
            India&apos;s funded startups,
            <span className={s.csModalTitleMuted}> curated for you</span>
          </h2>

          <p id={descId} className={s.csModalBody}>
            We&apos;re building a live feed of recently funded Indian startups — stage, sector,
            and hiring signals — so you can spot high-growth teams early. We&apos;re refining
            accuracy before opening it publicly.
          </p>

          <ul className={s.csModalList}>
            {MODAL_FEATURES.map((item) => (
              <li key={item} className={s.csModalListItem}>
                <span className={s.csModalListIcon} aria-hidden="true">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div className={s.csModalActions}>
            <button type="button" className={s.csModalPrimary} onClick={onClose}>
              Got it
            </button>
            <a href="/sign-in?role=candidate" className={s.csModalSecondary}>
              Get started with Mitra →
            </a>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function FundedStartupsComingSoonProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const openModal = useCallback(() => setOpen(true), []);
  const closeModal = useCallback(() => setOpen(false), []);

  return (
    <FundedStartupsCtx.Provider value={{ open: openModal }}>
      {children}
      <ComingSoonModal open={open} onClose={closeModal} />
    </FundedStartupsCtx.Provider>
  );
}

export function FundedStartupsTrigger({
  children,
  variant,
  className,
}: {
  children: ReactNode;
  variant: TriggerVariant;
  className?: string;
}) {
  const { open } = useFundedStartupsComingSoon();

  const variantClass =
    variant === "nav"
      ? s.csNavLink
      : variant === "footer"
        ? s.csFooterLink
        : s.heroSecondaryCta;

  return (
    <span className={`${s.csTriggerWrap} ${s[`csTriggerWrap--${variant}`]}`}>
      <button
        type="button"
        className={`${variantClass}${className ? ` ${className}` : ""}`}
        onClick={open}
      >
        {children}
      </button>
      <span className={s.csFloatBadge} aria-hidden="true">
        Coming soon
      </span>
    </span>
  );
}
