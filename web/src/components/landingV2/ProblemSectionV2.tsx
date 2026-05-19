"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import s from "./landing-v2.module.css";

/* ── Count-up hook ────────────────────────────────────────── */

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

/* ── Scroll-reveal wrapper ────────────────────────────────── */

function RevealCard({
  children,
  delay = 0,
  onVisible,
}: {
  children: React.ReactNode;
  delay?: number;
  onVisible?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const fired = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !fired.current) {
          fired.current = true;
          setVisible(true);
          onVisible?.();
          observer.disconnect();
        }
      },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [onVisible]);

  return (
    <div
      ref={ref}
      className={`${s.revealCard} ${visible ? s.inView : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/* ── Stat components ──────────────────────────────────────── */

function CountStat({ value, suffix, active }: { value: number; suffix: string; active: boolean }) {
  const count = useCountUp(value, 1100, active);
  return <>{count}{suffix}</>;
}

/* ── Pain card data ───────────────────────────────────────── */

const PAIN_CARDS = [
  {
    statType: "count" as const,
    statValue: 40,
    statSuffix: "%",
    label: "of listings aren't real",
    title: "Ghost jobs",
    body: "Companies post to build pipelines, benchmark salaries, or satisfy HR policy. You have no way to know which roles were ever meant to be filled — so you spend hours tailoring applications to a void.",
  },
  {
    statType: "count" as const,
    statValue: 3,
    statSuffix: "",
    label: "replies from 47 applications — average",
    title: "The black hole",
    body: "Your CV lands in a system managed by people who didn't write the JD, for a hiring manager who may have already decided internally. No relationship. No accountability. No response.",
  },
  {
    statType: "arrow" as const,
    statValue: 0,
    statSuffix: "",
    label: "how hiring managers perceive open signals",
    title: "The visibility trap",
    body: "The best candidates appear to be sought out, not searching. But the current system gives you no way to be found without announcing yourself — which changes how you're perceived the moment you do.",
  },
] as const;

/* ── Component ────────────────────────────────────────────── */

export function ProblemSectionV2() {
  const [active, setActive] = useState([false, false, false]);

  const markActive = useCallback((i: number) => {
    setActive((prev) => {
      if (prev[i]) return prev;
      const next = [...prev] as [boolean, boolean, boolean];
      next[i] = true;
      return next;
    });
  }, []);

  return (
    <section className={`${s.sectionWrap} ${s.problemSection}`}>
      <div className={s.sectionInner}>
        <p
          className={`${s.sectionLabel} ${s.fadeUp}`}
          style={{ "--anim-delay": "0ms" } as React.CSSProperties}
        >
          The current alternative
        </p>
        <h2
          className={`${s.sectionTitle} ${s.fadeUp}`}
          style={{ "--anim-delay": "80ms" } as React.CSSProperties}
        >
          Why the default approach fails.
        </h2>

        <div className={s.hiwSteps}>
          {PAIN_CARDS.map((card, i) => (
            <RevealCard key={card.title} delay={i * 130} onVisible={() => markActive(i)}>
              <div className={`${s.hiwStep} ${s.problemCard}`}>
                <div className={s.problemCardStat}>
                  {card.statType === "count" ? (
                    <CountStat value={card.statValue} suffix={card.statSuffix} active={active[i]} />
                  ) : (
                    <span className={s.problemArrow} aria-hidden="true">↓</span>
                  )}
                </div>
                <p className={s.problemCardStatLabel}>{card.label}</p>
                <div className={s.problemCardDivider} aria-hidden="true" />
                <h3 className={s.hiwStepTitle}>{card.title}</h3>
                <p className={s.hiwStepBody}>{card.body}</p>
              </div>
            </RevealCard>
          ))}
        </div>

        <div
          className={`${s.problemPivot} ${s.fadeUp}`}
          style={{ "--anim-delay": "500ms" } as React.CSSProperties}
        >
          <p className={s.problemPivotText}>
            Mitra doesn&apos;t fix these problems.{" "}
            <strong>It sidesteps them entirely.</strong>
          </p>
        </div>
      </div>
    </section>
  );
}
