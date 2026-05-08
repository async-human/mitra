"use client";

import { useEffect, useRef, useState } from "react";
import { useAudience } from "./AudienceContext";
import { Reveal } from "./Reveal";

function useCountUp(target: number, duration = 1600) {
  const [count, setCount] = useState(0);
  const [active, setActive] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setActive(true); obs.disconnect(); } },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!active || target === 0) { if (target === 0) setCount(0); return; }
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setCount(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [active, target, duration]);

  return { count, ref };
}

type StatDef = {
  num: number;
  prefix?: string;
  suffix?: string;
  display?: string; // override entire value (non-numeric)
  label: React.ReactNode;
};

function StatCell({ s, index }: { s: StatDef; index: number }) {
  const { count, ref } = useCountUp(s.num, 1600 + index * 100);

  return (
    <div className="stat-cell" ref={ref}>
      <div className="stat-n" aria-label={s.display ?? `${s.prefix ?? ""}${s.num}${s.suffix ?? ""}`}>
        {s.display ? (
          s.display
        ) : (
          <>
            {s.prefix}<span className="stat-count">{count}</span>
            {s.suffix && <sup>{s.suffix}</sup>}
          </>
        )}
      </div>
      <div className="stat-l">{s.label}</div>
    </div>
  );
}

const CANDIDATE_STATS: StatDef[] = [
  { num: 8, suffix: "d", label: <>Average days to first<br />interview after intro</> },
  { num: 0, display: "0", label: <>Candidates ghosted —<br />our iron promise</> },
  { num: 6, prefix: "₹", suffix: "L+", label: <>Average extra salary<br />negotiated per candidate</> },
  { num: 0, display: "Free", label: <>For candidates —<br />forever, no asterisk</> },
];

const FOUNDER_STATS: StatDef[] = [
  { num: 8, suffix: "%", label: <>Success fee — half what<br />agencies charge</> },
  { num: 0, display: "3–5", label: <>Pre-qualified intros<br />per role per week</> },
  { num: 90, suffix: "d", label: <>Replacement guarantee<br />in writing, no fine print</> },
  { num: 24, suffix: "h", label: <>Time to activation<br />after you share the role</> },
];

export function Stats() {
  const { audience } = useAudience();
  const stats = audience === "candidate" ? CANDIDATE_STATS : FOUNDER_STATS;

  return (
    <section className="stats-sec" aria-label="Mitra by the numbers">
      <div className="stats-row">
        {stats.map((s, i) => <StatCell key={i} s={s} index={i} />)}
      </div>
      <Reveal delay={2}>
        <p className="stats-disclaimer">
          Headline numbers reflect our operating model and typical pipeline
          pacing; they are{" "}
          <strong>not audited metrics</strong>. Ask us how any of these work in
          practice on WhatsApp.
        </p>
      </Reveal>
    </section>
  );
}
