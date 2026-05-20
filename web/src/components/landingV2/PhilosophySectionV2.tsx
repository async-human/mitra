"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const PRINCIPLES = {
  candidate: [
    {
      title: "Supervised before autonomous",
      body: "Mitra earns autonomy through demonstrated judgment. Every new category of action is supervised before it's automated. We tell you what the agent is doing and why.",
    },
    {
      title: "Outcomes over activity",
      body: "The only metric that matters is placements that stick. Not messages sent. Not matches shown. Candidates happy at 90 days. Founders who come back.",
    },
    {
      title: "Radical transparency",
      body: "We publish our roadmap. We explain how matching works. We tell candidates if a salary is below market even when it costs us the placement fee. Trust is the product.",
    },
  ],
  company: [
    {
      title: "Your bar, learned over time",
      body: "Every pass and every hire teaches Mitra what you actually respond to — not what's on the JD. Shortlists sharpen with each placement.",
    },
    {
      title: "Outcomes over activity",
      body: "We measure success in hires that stick at 90 days — not CVs submitted or interviews scheduled. If it doesn't lead to a great hire, it doesn't count.",
    },
    {
      title: "Radical transparency",
      body: "Clear fees, written guarantees, and no spray-and-pray intros. You see why each candidate was introduced and what Mitra knows about their intent.",
    },
  ],
};

const COPY = {
  candidate: {
    quote: "The professional internet deserved better infrastructure than this.",
    sub: (
      <>
        Mitra is that infrastructure. The candidate still decides whether to take
        the role. The founder still decides whether to make the offer.
        Everything between those two moments&nbsp;&mdash; the signal, the context,
        the introduction&nbsp;&mdash; that&apos;s what Mitra owns.
      </>
    ),
  },
  company: {
    quote: "Hiring engineers shouldn't feel like fighting an algorithm.",
    sub: (
      <>
        Mitra is the layer between your brief and the conversation that matters.
        You still choose who to meet and who to hire. Mitra owns the signal,
        the context, and the introduction&nbsp;&mdash; so every hour you spend
        is on people who already want to be there.
      </>
    ),
  },
};

export function PhilosophySectionV2({ audience }: { audience: V2Audience }) {
  const c = COPY[audience];
  const principles = PRINCIPLES[audience];
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section
      ref={ref}
      className={`${s.philosophy} ${inView ? s.philosophyInView : ""}`}
      id="philosophy"
    >
      <div className={s.philosophyInner} key={audience}>
        <p className={s.philosophyLabel}>The product philosophy</p>

        <h2 className={s.philosophyQuote}>&ldquo;{c.quote}&rdquo;</h2>

        <p className={s.philosophySub}>{c.sub}</p>

        <div className={s.philosophyPrinciples}>
          {principles.map((p, i) => (
            <div
              key={p.title}
              className={s.philosophyCard}
              style={{ transitionDelay: `${i * 80}ms` }}
            >
              <h3 className={s.philosophyCardTitle}>{p.title}</h3>
              <p className={s.philosophyCardBody}>{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
