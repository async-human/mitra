"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
      },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
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

const JOURNEY = {
  candidate: [
    {
      day: "MON",
      title: "Brief Mitra",
      desc: "A 2-minute WhatsApp chat — what you want to own, where you're headed, what would make you say yes",
    },
    {
      day: "WED",
      title: "Your profile goes out",
      desc: "Mitra introduces you to a matched founder with full context — not a CV, a story",
    },
    {
      day: "THU",
      title: "Founder replies",
      desc: "They already know who you are. This is a warm conversation, not a cold call",
    },
  ],
  company: [
    {
      day: "MON",
      title: "Post the role",
      desc: "A 2-minute brief — Mitra researches your company and builds a real hiring profile, not just a JD",
    },
    {
      day: "WED",
      title: "Candidates scored",
      desc: "Mitra ranks its active pool by skill fit, salary fit, startup readiness, and motivation",
    },
    {
      day: "THU",
      title: "First intro arrives",
      desc: "A pre-qualified engineer, fully briefed on your role — already interested, not cold",
    },
  ],
};

const LABEL = {
  candidate: "What to expect",
  company: "How it starts",
};

const TITLE = {
  candidate: "Three days to your first conversation.",
  company: "Brief to first intro in 48 hours.",
};

function ArrowConnector() {
  return (
    <div className={s.djConnector} aria-hidden="true">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export function DayJourneySection({ audience }: { audience: V2Audience }) {
  const steps = JOURNEY[audience];

  return (
    <section className={s.djSection} key={audience}>
      <div className={s.djInner}>
        <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
          {LABEL[audience]}
        </p>
        <h2 className={`${s.sectionTitle} ${s.fadeUp}`} style={{ "--anim-delay": "80ms" } as React.CSSProperties}>
          {TITLE[audience]}
        </h2>

        <div className={s.djCards}>
          {steps.map((step, i) => (
            <Fragment key={step.day}>
              <RevealCard delay={i * 120}>
                <div className={s.djCard}>
                  <span className={s.djDay}>{step.day}</span>
                  <p className={s.djTitle}>{step.title}</p>
                  <p className={s.djDesc}>{step.desc}</p>
                </div>
              </RevealCard>
              {i < steps.length - 1 && <ArrowConnector />}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}
