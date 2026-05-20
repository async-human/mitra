"use client";

import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

const ROLES = [
  { title: "Backend Engineer", color: "#F59E0B" },
  { title: "Founding Engineer", color: "#10B981" },
  { title: "Platform Engineer", color: "#3B82F6" },
  { title: "Staff Engineer", color: "#8B5CF6" },
  { title: "DevOps / SRE", color: "#F97316" },
  { title: "ML Engineer", color: "#06B6D4" },
  { title: "Full-stack Engineer", color: "#EC4899" },
  { title: "Frontend Engineer", color: "#84CC16" },
  { title: "Data Engineer", color: "#A78BFA" },
  { title: "Mobile Engineer", color: "#34D399" },
  { title: "Head of Engineering", color: "#60A5FA" },
  { title: "Engineering Manager", color: "#C084FC" },
  { title: "Technical Lead", color: "#2DD4BF" },
  { title: "Senior SDE-II / III", color: "#FB923C" },
  { title: "Founding ML Eng", color: "#F472B6" },
  { title: "Infrastructure Eng", color: "#A3E635" },
];

function RolePills() {
  const items = [...ROLES, ...ROLES];
  return (
    <div className={s.chRolesTrack}>
      {items.map((role, i) => (
        <div key={`${role.title}-${i}`} className={s.chPill}>
          <span className={s.chPillDot} style={{ background: role.color }} />
          <span className={s.chPillText}>{role.title}</span>
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
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section ref={ref} className={`${s.chSection} ${inView ? s.chSectionInView : ""}`}>
      <div className={s.chCard}>
        <div className={s.chLeft}>
          <p className={s.chLeftLabel}>Built for startups hiring engineers</p>
          <h2 className={s.chHeadline}>
            Find the engineer you can&apos;t find on LinkedIn.
          </h2>
          <p className={s.chLeftSub}>
            One 2-minute brief. Mitra researches your company, scores its
            candidate pool, and delivers matched engineers — no recruiter,
            no job board, no noise.
          </p>
          <ul className={s.chLeftBullets}>
            <li>First 2 hires free</li>
            <li>3–5 intros per week with full context</li>
            <li>8% fee · 90-day replacement guarantee</li>
          </ul>
        </div>

        <div className={s.chRight}>
          <p className={s.chRightLabel}>In 48 hours</p>
          <p className={s.chRightTitle}>Find your next:</p>

          <div className={s.chRolesWrap}>
            <div className={s.chRolesMarquee}>
              <RolePills />
            </div>
            <div className={s.chRolesFade} aria-hidden="true" />
          </div>

          <a
            href={whatsAppHrefFor("founder")}
            target="_blank"
            rel="noopener noreferrer"
            className={s.chCta}
          >
            Post a role — first 2 hires free →
          </a>
          <p className={s.chCtaNote}>No recruiter fees · 90-day replacement guarantee</p>
        </div>
      </div>
    </section>
  );
}
