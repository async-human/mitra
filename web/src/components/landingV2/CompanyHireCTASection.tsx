"use client";

import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

const SHORTLIST = [
  { initials: "PM", name: "Priya M.", meta: "5 yrs · Razorpay infra", salary: "₹52L", fit: 94 },
  { initials: "AK", name: "Arjun K.", meta: "4 yrs · Platform · Setu", salary: "₹46L", fit: 88 },
  { initials: "NR", name: "Nisha R.", meta: "3 yrs · Backend · CRED", salary: "₹38L", fit: 81 },
];

const ROLES = [
  "Founding Engineer",
  "Platform Engineer",
  "Staff Engineer",
  "ML Engineer",
  "Head of Engineering",
  "DevOps / SRE",
  "Backend Lead",
  "Full-stack Engineer",
  "Security Engineer",
  "Data Engineer",
];

const STATS = [
  { value: "48h", label: "to first shortlist" },
  { value: "3–5", label: "intros per week" },
  { value: "2", label: "first hires free" },
];

function RoleTicker() {
  const items = [...ROLES, ...ROLES];
  return (
    <div className={s.chTicker} aria-hidden="true">
      <div className={s.chTickerTrack}>
        {items.map((role, i) => (
          <span key={`${role}-${i}`} className={s.chTickerPill}>
            {role}
          </span>
        ))}
      </div>
    </div>
  );
}

function ShortlistCard({
  candidate,
  delay,
  active,
}: {
  candidate: (typeof SHORTLIST)[number];
  delay: number;
  active: boolean;
}) {
  return (
    <div
      className={`${s.chCandidate} ${active ? s.chCandidateIn : ""}`}
      style={{ "--card-delay": `${delay}ms` } as React.CSSProperties}
    >
      <div className={s.chCandidateAv}>{candidate.initials}</div>
      <div className={s.chCandidateBody}>
        <div className={s.chCandidateTop}>
          <span className={s.chCandidateName}>{candidate.name}</span>
          <span className={s.chCandidateFit}>{candidate.fit}% fit</span>
        </div>
        <div className={s.chCandidateMeta}>{candidate.meta}</div>
        <div className={s.chCandidateBarTrack}>
          <div
            className={`${s.chCandidateBar} ${active ? s.chCandidateBarGrow : ""}`}
            style={{ "--fit": `${candidate.fit}%`, "--bar-delay": `${delay + 200}ms` } as React.CSSProperties}
          />
        </div>
      </div>
      <span className={s.chCandidateSalary}>{candidate.salary}</span>
    </div>
  );
}

export function CompanyHireCTASection() {
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
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section ref={ref} className={`${s.chSection} ${inView ? s.chSectionInView : ""}`}>
      <div className={s.chCard}>
        <div className={s.chAccentRail} aria-hidden="true" />

        <div className={s.chMain}>
          <header className={s.chHeader}>
            <p className={s.chEyebrow}>For founders hiring engineers</p>
            <h2 className={s.chHeadline}>
              Your shortlist —<br />
              <span className={s.chHeadlineAccent}>not a job board.</span>
            </h2>
            <p className={s.chSub}>
              Brief Mitra once. Get engineers who match your stage, stack, and bar —
              each intro arrives with motivation notes and fit context attached.
            </p>
          </header>

          <div className={s.chStats}>
            {STATS.map(({ value, label }) => (
              <div key={label} className={s.chStat}>
                <span className={s.chStatValue}>{value}</span>
                <span className={s.chStatLabel}>{label}</span>
              </div>
            ))}
          </div>

          <div className={s.chShortlistPanel}>
            <div className={s.chShortlistHead}>
              <span className={s.chShortlistLabel}>This week&apos;s shortlist</span>
              <span className={s.chShortlistLive}>
                <span className={s.chShortlistLiveDot} />
                Live preview
              </span>
            </div>
            <div className={s.chShortlistCards}>
              {SHORTLIST.map((c, i) => (
                <ShortlistCard key={c.initials} candidate={c} delay={i * 120} active={inView} />
              ))}
            </div>
          </div>

          <RoleTicker />

          <div className={s.chFooter}>
            <a
              href={whatsAppHrefFor("founder")}
              target="_blank"
              rel="noopener noreferrer"
              className={s.chCta}
            >
              Post a role on WhatsApp
              <span className={s.chCtaArrow} aria-hidden="true">→</span>
            </a>
            <p className={s.chFootnote}>8% success fee · 90-day replacement guarantee</p>
          </div>
        </div>
      </div>
    </section>
  );
}
