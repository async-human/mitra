"use client";

import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

type RolePill = { title: string; dot: string };

const COL_A: RolePill[] = [
  { title: "Founding Engineer", dot: "#C8421A" },
  { title: "Platform Engineer", dot: "#8B5A2E" },
  { title: "Staff Engineer", dot: "#5C4030" },
  { title: "Backend Lead", dot: "#D07038" },
  { title: "Infrastructure Eng", dot: "#9A3D1F" },
  { title: "DevOps / SRE", dot: "#B85A32" },
];

const COL_B: RolePill[] = [
  { title: "Senior SDE-II", dot: "#7A3018" },
  { title: "ML Engineer", dot: "#C8421A" },
  { title: "Full-stack Engineer", dot: "#A0522D" },
  { title: "Head of Engineering", dot: "#6B4423" },
  { title: "Technical Lead", dot: "#E07040" },
  { title: "Security Engineer", dot: "#8B4513" },
];

const COL_C: RolePill[] = [
  { title: "Data Engineer", dot: "#9A3D1F" },
  { title: "Frontend Engineer", dot: "#C8421A" },
  { title: "Systems Engineer", dot: "#5C4030" },
  { title: "Mobile Engineer", dot: "#B85A32" },
  { title: "Applied AI Eng", dot: "#D07038" },
  { title: "Site Reliability", dot: "#7A3018" },
];

function RoleColumn({
  roles,
  reverse,
  duration,
}: {
  roles: RolePill[];
  reverse?: boolean;
  duration: number;
}) {
  const items = [...roles, ...roles];
  return (
    <div className={s.chRoleCol}>
      <div
        className={`${s.chRoleColTrack} ${reverse ? s.chRoleColTrackReverse : ""}`}
        style={{ animationDuration: `${duration}s` } as React.CSSProperties}
      >
        {items.map(({ title, dot }, i) => (
          <span key={`${title}-${i}`} className={s.chRolePill}>
            <span className={s.chRoleDot} style={{ background: dot }} />
            {title}
          </span>
        ))}
      </div>
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
          <h2 className={s.chHeadline}>Get your first intros.</h2>
          <p className={s.chSub}>
            One brief. A curated shortlist of engineers who actually want your stage —
            not a flood of CVs from people who never read the JD.
          </p>
        </div>

        <div className={s.chVisual}>
          <div className={s.chVisualHead}>
            <span className={s.chVisualLabel}>In 48 hours</span>
          </div>
          <h3 className={s.chVisualTitle}>Hire your next:</h3>

          <div className={s.chRoleGrid} aria-hidden="true">
            <RoleColumn roles={COL_A} duration={22} />
            <RoleColumn roles={COL_B} reverse duration={26} />
            <RoleColumn roles={COL_C} duration={24} />
          </div>

          <a
            href={whatsAppHrefFor("founder")}
            target="_blank"
            rel="noopener noreferrer"
            className={s.chCtaVisual}
          >
            List a role — first 2 hires free
            <span className={s.chCtaArrow} aria-hidden="true">→</span>
          </a>
          <p className={s.chVisualFoot}>No job board. No recruiter inbox.</p>
        </div>
      </div>
    </section>
  );
}
