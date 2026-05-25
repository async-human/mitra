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
import s from "./landing-v2.module.css";

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

  if (!open) return null;

  return (
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
        <button type="button" className={s.csClose} onClick={onClose} aria-label="Close">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>

        <div className={s.csModalGlow} aria-hidden="true" />

        <p className={s.csModalEyebrow}>
          <span className={s.csModalEyebrowDot} />
          Coming soon
        </p>

        <h2 id={titleId} className={s.csModalTitle}>
          India&apos;s funded startups,<br />
          <em>curated for you</em>
        </h2>

        <p id={descId} className={s.csModalBody}>
          We&apos;re building a live feed of recently funded Indian startups — funding stage,
          sector, and hiring signals — so you can spot high-growth teams before they hit the
          job boards. We&apos;re refining accuracy before we open it publicly.
        </p>

        <ul className={s.csModalList}>
          <li>Recently funded companies across fintech, SaaS, consumer, and more</li>
          <li>Stage, sector, and round details in one place</li>
          <li>Matched to roles Mitra can introduce you to</li>
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
