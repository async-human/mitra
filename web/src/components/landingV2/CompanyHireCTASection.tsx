"use client";

import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

const ROLES_ROW_A = [
  "Backend Engineer",
  "Founding Engineer",
  "Platform Engineer",
  "Staff Engineer",
  "DevOps / SRE",
  "ML Engineer",
  "Full-stack Engineer",
];

const ROLES_ROW_B = [
  "Frontend Engineer",
  "Data Engineer",
  "Head of Engineering",
  "Technical Lead",
  "Senior SDE-II",
  "Infrastructure Eng",
  "Security Engineer",
];

const SHORTLIST = [
  { initials: "PM", name: "Priya M.", meta: "5 yrs · Razorpay infra", salary: "₹52L", fit: 94 },
  { initials: "AK", name: "Arjun K.", meta: "4 yrs · Platform · Setu", salary: "₹46L", fit: 88 },
  { initials: "NR", name: "Nisha R.", meta: "3 yrs · Backend · CRED", salary: "₹38L", fit: 81 },
];

function RoleMarquee({ roles, reverse }: { roles: string[]; reverse?: boolean }) {
  const items = [...roles, ...roles];
  return (
    <div className={`${s.chMarquee} ${reverse ? s.chMarqueeReverse : ""}`}>
      <div className={s.chMarqueeTrack}>
        {items.map((title, i) => (
          <span key={`${title}-${i}`} className={s.chMarqueePill}>
            {title}
          </span>
        ))}
      </div>
    </div>
  );
}

function ShortlistPreview() {
  return (
    <div className={s.chShortlist}>
      <div className={s.chShortlistBadge}>✦ 3 matched this week</div>
      {SHORTLIST.map((c) => (
        <div key={c.initials} className={s.chShortlistRow}>
          <div className={s.chShortlistAv}>{c.initials}</div>
          <div className={s.chShortlistInfo}>
            <div className={s.chShortlistName}>
              {c.name}
              <span className={s.chShortlistSalary}>{c.salary}</span>
            </div>
            <div className={s.chShortlistMeta}>{c.meta}</div>
            <div className={s.chShortlistBarWrap}>
              <div className={s.chShortlistBar} style={{ width: `${c.fit}%` }} />
            </div>
          </div>
          <span className={s.chShortlistFit}>{c.fit}%</span>
        </div>
      ))}
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
      { threshold: 0.12 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section ref={ref} className={`${s.chSection} ${inView ? s.chSectionInView : ""}`}>
      <div className={s.chCard}>
        <div className={s.chCopy}>
          <p className={s.chEyebrow}>Built for startups hiring engineers</p>
          <h2 className={s.chHeadline}>
            Find the engineer you can&apos;t find on LinkedIn.
          </h2>
          <p className={s.chSub}>
            One 2-minute brief. Mitra researches your company and sends
            pre-qualified intros with full context — no recruiter, no job board.
          </p>
          <ul className={s.chPerks}>
            <li>First 2 hires free</li>
            <li>3–5 intros / week with motivation &amp; fit notes</li>
            <li>8% fee · 90-day replacement in writing</li>
          </ul>
          <a
            href={whatsAppHrefFor("founder")}
            target="_blank"
            rel="noopener noreferrer"
            className={s.chCta}
          >
            Post a role — first 2 hires free
            <span className={s.chCtaArrow} aria-hidden="true">→</span>
          </a>
        </div>

        <div className={s.chVisual}>
          <div className={s.chVisualHead}>
            <span className={s.chVisualLabel}>In 48 hours</span>
            <span className={s.chVisualTitle}>Your shortlist</span>
          </div>

          <ShortlistPreview />

          <div className={s.chRolesBlock}>
            <p className={s.chRolesLabel}>Roles we place most often</p>
            <RoleMarquee roles={ROLES_ROW_A} />
            <RoleMarquee roles={ROLES_ROW_B} reverse />
          </div>
        </div>
      </div>
    </section>
  );
}
