"use client";

import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const COMPANIES = ["Razorpay", "Setu", "CRED", "Groww", "Zepto", "BharatPe", "Fi Money"];

type ProofStat =
  | { label: string; display: string }
  | { label: string; num: number; suffix: string };

const STATS: Record<V2Audience, ProofStat[]> = {
  candidate: [
    { label: "Engineers placed", display: "50+" },
    { label: "Avg. time to first interview", display: "8 days" },
    { label: "Founder response rate", display: "90%+" },
    { label: "Cost to candidates", display: "₹0" },
  ],
  company: [
    { label: "Successful placements", num: 50, suffix: "+" },
    { label: "Success fee — half agency rate", num: 8, suffix: "%" },
    { label: "Replacement guarantee", num: 90, suffix: "d" },
    { label: "First hires free", num: 2, suffix: "" },
  ],
};

const CTA = {
  candidate: { label: "Get started — free →", href: whatsAppHrefFor("candidate") },
  company: { label: "List a role →", href: whatsAppHrefFor("founder") },
};

function useCountUp(target: number, active: boolean) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    let raf: number;
    const start = performance.now();
    const duration = 900;
    const tick = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(eased * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active]);
  return value;
}

function AnimatedStat({
  num,
  suffix,
  active,
}: {
  num: number;
  suffix: string;
  active: boolean;
}) {
  const count = useCountUp(num, active);
  return (
    <>
      {count}
      {suffix}
    </>
  );
}

export function ProofV2({ audience }: { audience: V2Audience }) {
  const cta = CTA[audience];
  const stats = STATS[audience];
  const sectionRef = useRef<HTMLElement>(null);
  const [statsActive, setStatsActive] = useState(false);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setStatsActive(true);
          obs.disconnect();
        }
      },
      { threshold: 0.2 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section className={s.proof} ref={sectionRef}>
      <div className={`${s.proofInner} ${s.audiencePane}`} key={audience}>
        <div className={s.proofRow}>
          <div className={s.proofStats}>
            {stats.map((stat) => (
              <div key={stat.label}>
                <div className={s.proofStatNum}>
                  {"display" in stat ? (
                    stat.display
                  ) : (
                    <AnimatedStat
                      num={stat.num}
                      suffix={stat.suffix}
                      active={statsActive}
                    />
                  )}
                </div>
                <div className={s.proofStatLabel}>{stat.label}</div>
              </div>
            ))}
          </div>
          <a
            href={cta.href}
            target="_blank"
            rel="noopener noreferrer"
            className={s.proofCta}
          >
            {cta.label}
          </a>
        </div>

        <div className={s.proofCompaniesRow}>
          <span className={s.proofCompaniesLabel}>Engineers placed at</span>
          <div className={s.proofCompaniesMarquee}>
            <div className={s.proofCompaniesTrack}>
              {[...COMPANIES, ...COMPANIES].map((c, i) => (
                <span key={`${c}-${i}`} className={s.proofCompanyTag}>
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
