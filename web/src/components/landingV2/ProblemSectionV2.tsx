"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import {
  PROBLEM_CANDIDATE_SCENARIOS,
  PROBLEM_FOUNDER_SCENARIOS,
  type ProblemScenario,
} from "@/lib/landingDynamic";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const ROTATE_MS = 7500;

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

function usePrefersReducedMotion(): boolean {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduce(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return reduce;
}

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
      { threshold: 0, rootMargin: "0px 0px -60px 0px" },
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

function CountStat({
  value,
  suffix,
  active,
}: {
  value: number;
  suffix: string;
  active: boolean;
}) {
  const count = useCountUp(value, 1100, active);
  return (
    <>
      {count}
      {suffix}
    </>
  );
}

function ScenarioRotor({
  scenarios,
  reduceMotion,
}: {
  scenarios: ProblemScenario[];
  reduceMotion: boolean;
}) {
  const baseId = useId().replace(/:/g, "");
  const [idx, setIdx] = useState(0);

  const tick = useCallback(() => {
    setIdx((i) => (i + 1) % scenarios.length);
  }, [scenarios.length]);

  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(tick, ROTATE_MS);
    return () => window.clearInterval(id);
  }, [reduceMotion, tick]);

  const sc = scenarios[idx]!;

  return (
    <div className={s.problemRotorWrap}>
      <div
        id={`${baseId}-rotor`}
        className={s.problemRotor}
        role="region"
        aria-roledescription="Rotating examples"
        aria-live={reduceMotion ? "off" : "polite"}
      >
        <div key={sc.id} className={s.problemRotorPane}>
          <p className={s.problemRotorHook}>&ldquo;{sc.hook}&rdquo;</p>
          <p className={s.problemRotorDetail}>{sc.detail}</p>
          <span className={s.problemRotorTag}>{sc.tag}</span>
        </div>
      </div>
      <div className={s.problemRotorDots} role="tablist" aria-label="Example">
        {scenarios.map((item, i) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={i === idx}
            className={`${s.problemRotorDot} ${i === idx ? s.problemRotorDotActive : ""}`}
            onClick={() => setIdx(i)}
          />
        ))}
      </div>
    </div>
  );
}

const CANDIDATE_PAIN_CARDS = [
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

const FOUNDER_PAIN_CARDS = [
  {
    statType: "count" as const,
    statValue: 12,
    statSuffix: "",
    label: "who can explain your stack — out of 184 applicants",
    title: "Volume isn't signal",
    body: "Job boards optimise for applications, not fit. Your team spends a sprint screening people who never wanted your problem in the first place.",
  },
  {
    statType: "count" as const,
    statValue: 5,
    statSuffix: "",
    label: "pre-qualified intros per week — not CV dumps",
    title: "Introductions, not pipelines",
    body: "Each intro arrives with motivation, timeline, and why they want your company specifically. You meet people ready for a real conversation.",
  },
  {
    statType: "count" as const,
    statValue: 90,
    statSuffix: "d",
    label: "replacement guarantee — in writing",
    title: "Aligned incentives",
    body: "We only earn when you hire. If someone leaves within 90 days, we replace them at no cost. No retainers on the first two hires.",
  },
] as const;

export function ProblemSectionV2({ audience }: { audience: V2Audience }) {
  const isCompany = audience === "company";
  const painCards = isCompany ? FOUNDER_PAIN_CARDS : CANDIDATE_PAIN_CARDS;
  const reduceMotion = usePrefersReducedMotion();
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
      <div className={s.sectionInner} key={audience}>
        <p
          className={`${s.sectionLabel} ${s.fadeUp}`}
          style={{ "--anim-delay": "0ms" } as React.CSSProperties}
        >
          {isCompany ? "What founders tell us" : "The current alternative"}
        </p>
        <h2
          className={`${s.sectionTitle} ${s.fadeUp}`}
          style={{ "--anim-delay": "80ms" } as React.CSSProperties}
        >
          {isCompany
            ? "You're drowning in noise. You need signal."
            : "Why the default approach fails."}
        </h2>

        {isCompany && (
          <div
            className={`${s.fadeUp} ${s.problemRotorSlot}`}
            style={{ "--anim-delay": "160ms" } as React.CSSProperties}
          >
            <ScenarioRotor
              scenarios={PROBLEM_FOUNDER_SCENARIOS}
              reduceMotion={reduceMotion}
            />
          </div>
        )}

        <div className={s.hiwSteps}>
          {painCards.map((card, i) => (
            <RevealCard key={card.title} delay={i * 130} onVisible={() => markActive(i)}>
              <div className={`${s.hiwStep} ${s.problemCard}`}>
                <div className={s.problemCardStat}>
                  {card.statType === "count" ? (
                    <CountStat
                      value={card.statValue}
                      suffix={card.statSuffix}
                      active={active[i]}
                    />
                  ) : (
                    <span className={s.problemArrow} aria-hidden="true">
                      ↓
                    </span>
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
            {isCompany ? (
              <>
                Mitra doesn&apos;t add another ATS.{" "}
                <strong>It sends people who already want to build with you.</strong>
              </>
            ) : (
              <>
                Mitra doesn&apos;t fix these problems.{" "}
                <strong>It sidesteps them entirely.</strong>
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  );
}
