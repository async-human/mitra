"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

function useCountUp(target: number, duration = 1100, active = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, active]);
  return value;
}

const CONTENT = {
  candidate: {
    eyebrow: "The current reality",
    statA: { num: 47, label: "average applications sent" },
    statB: { num: 3,  label: "replies back" },
    context: "That's not a you problem. That's the market.",
    punch: "Mitra removes you from this equation entirely.",
    punchSub: "You don't apply. You get introduced — by an agent that already knows your story.",
    cta: { label: "See how it works", href: "#how-it-works", external: false },
  },
  company: {
    eyebrow: "Most hiring pipelines",
    statA: { num: 184, label: "applicants per role" },
    statB: { num: 12,  label: "can explain your stack" },
    context: "Your team spends a sprint on the other 172.",
    punch: "Mitra only sends you the 12.",
    punchSub: "Pre-qualified. Full context on motivation, timeline, and why they want your problem.",
    cta: { label: "List a role — first 2 free", href: whatsAppHrefFor("founder"), external: true },
  },
};

export function ProblemV3({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(false);
  const fired = useRef(false);

  const onVisible = useCallback(() => {
    if (!fired.current) { fired.current = true; setActive(true); }
  }, []);

  useEffect(() => {
    fired.current = false;
    setActive(false);
  }, [audience]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onVisible(); },
      { threshold: 0.15 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [onVisible]);

  const numA = useCountUp(c.statA.num, 1000, active);
  const numB = useCountUp(c.statB.num, 900,  active);

  return (
    <section className={s.problemV3Section}>
      <div className={s.problemV3Inner} ref={ref} key={audience}>

        {/* LEFT — the problem as raw numbers */}
        <div className={s.problemV3Left}>
          <p className={s.problemV3Eyebrow}>{c.eyebrow}</p>

          <div className={s.problemV3StatGroup}>
            <div className={s.problemV3StatRow}>
              <span className={s.problemV3Num}>{numA}</span>
              <span className={s.problemV3NumLabel}>{c.statA.label}</span>
            </div>
          </div>

          <span className={s.problemV3Arrow} aria-hidden="true">↓</span>

          <div className={s.problemV3StatGroup}>
            <div className={s.problemV3StatRow}>
              <span className={`${s.problemV3Num} ${s.problemV3NumMuted}`}>{numB}</span>
              <span className={s.problemV3NumLabel}>{c.statB.label}</span>
            </div>
          </div>

          <p className={s.problemV3Context}>{c.context}</p>
        </div>

        {/* RIGHT — Mitra's response */}
        <div className={s.problemV3Right}>
          <p className={s.problemV3Punch}>{c.punch}</p>
          <p className={s.problemV3PunchSub}>{c.punchSub}</p>
          {c.cta.external ? (
            <a href={c.cta.href} target="_blank" rel="noopener noreferrer" className={s.problemV3Link}>
              {c.cta.label} →
            </a>
          ) : (
            <a href={c.cta.href} className={s.problemV3Link}>
              {c.cta.label} →
            </a>
          )}
        </div>

      </div>
    </section>
  );
}
