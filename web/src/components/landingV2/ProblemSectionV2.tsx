"use client";

import { useEffect, useRef, useState } from "react";
import s from "./landing-v2.module.css";

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

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

const PAIN_CARDS = [
  {
    stat: "40%",
    label: "of listings aren't real",
    title: "Ghost jobs",
    body: "Companies post to build pipelines, benchmark salaries, or satisfy HR policy. You have no way to know which roles were ever meant to be filled. You spend hours tailoring applications to a void.",
  },
  {
    stat: "3",
    label: "replies from 47 applications — average",
    title: "The black hole",
    body: "Your CV lands in a system managed by people who didn't write the JD, for a hiring manager who may have already decided internally. No relationship. No accountability. No response.",
  },
  {
    stat: "↓",
    label: "how hiring managers perceive open signals",
    title: "The visibility trap",
    body: "The best candidates appear to be sought out, not searching. But the current system gives you no way to be found without announcing yourself — which changes how you're perceived the moment you do.",
  },
];

export function ProblemSectionV2() {
  return (
    <section className={s.sectionWrap}>
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
          {PAIN_CARDS.map(({ stat, label, title, body }, i) => (
            <RevealCard key={title} delay={i * 110}>
              <div className={`${s.hiwStep} ${s.problemCard}`}>
                <div className={s.problemCardStat}>{stat}</div>
                <p className={s.problemCardStatLabel}>{label}</p>
                <h3 className={s.hiwStepTitle}>{title}</h3>
                <p className={s.hiwStepBody}>{body}</p>
              </div>
            </RevealCard>
          ))}
        </div>

        <div
          className={`${s.problemPivot} ${s.fadeUp}`}
          style={{ "--anim-delay": "400ms" } as React.CSSProperties}
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
