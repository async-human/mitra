"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); observer.disconnect(); } },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={`${s.revealCard} ${visible ? s.inView : ""}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function IconChat() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v7a2 2 0 01-2 2H7l-4 3V5z" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="5.5" />
      <path d="M16 16l-3-3" />
    </svg>
  );
}

function IconArrow() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 10h12M11 5l5 5-5 5" />
    </svg>
  );
}

function IconDoc() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="12" height="16" rx="2" />
      <path d="M8 7h4M8 10h4M8 13h2" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="7" r="3" />
      <path d="M2 17c0-3.314 2.686-5 6-5s6 1.686 6 5" />
      <path d="M14 5a3 3 0 010 6M18 17c0-2.5-1.5-4-4-4" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="8" />
      <path d="M6.5 10.5l2.5 2.5 4.5-5" />
    </svg>
  );
}

const STEPS = {
  candidate: [
    {
      num: "Step 01", Icon: IconChat,
      title: "Talk to Mitra — it listens and learns",
      tagline: "A WhatsApp conversation that goes deeper than your CV.",
    },
    {
      num: "Step 02", Icon: IconSearch,
      title: "Matches that improve over time",
      tagline: "Ranked against funded startups on what you actually want — not keywords.",
    },
    {
      num: "Step 03", Icon: IconArrow,
      title: "A warm intro that genuinely lands",
      tagline: "The founder already knows your story before the first call. Response rate: 90%+.",
    },
  ],
  company: [
    {
      num: "Step 01", Icon: IconDoc,
      title: "Brief us on the role once",
      tagline: "Tell us what good looks like in 90 days. Mitra remembers across every search.",
    },
    {
      num: "Step 02", Icon: IconUsers,
      title: "We find candidates with genuine intent",
      tagline: "Filtered for people motivated to join your stage — not just open to opportunities.",
    },
    {
      num: "Step 03", Icon: IconCheck,
      title: "Introductions, not CVs. And it gets sharper.",
      tagline: "3–5 intros/week with full context. Every action you take sharpens the next shortlist.",
    },
  ],
};

const TITLE = {
  candidate: "A companion that gets smarter the more you talk.",
  company: "From brief to shortlist. Sharper every time.",
};

export function HowItWorksV3({ audience }: { audience: V2Audience }) {
  return (
    <section className={s.sectionWrap} id="how-it-works">
      <div className={s.sectionInner} key={audience}>
        <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
          How it works
        </p>
        <h2 className={`${s.sectionTitle} ${s.fadeUp}`} style={{ "--anim-delay": "80ms" } as React.CSSProperties}>
          {TITLE[audience]}
        </h2>
        <div className={s.hiwSteps}>
          {STEPS[audience].map(({ num, Icon, title, tagline }, i) => (
            <RevealCard key={num} delay={i * 110}>
              <div className={s.hiwStep}>
                <p className={s.hiwStepNum}>{num}</p>
                <div className={s.hiwStepIcon} aria-hidden="true"><Icon /></div>
                <h3 className={s.hiwStepTitle}>{title}</h3>
                <p className={s.hiwV3Tagline}>{tagline}</p>
              </div>
            </RevealCard>
          ))}
        </div>
      </div>
    </section>
  );
}
