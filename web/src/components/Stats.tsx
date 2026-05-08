"use client";

import type { ReactNode } from "react";
import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

const CANDIDATE_STATS: { value: ReactNode; label: ReactNode }[] = [
  { value: <>8<sup>d</sup></>, label: <>Average days to first<br />interview after intro</> },
  { value: "0", label: <>Candidates ghosted —<br />our iron promise</> },
  { value: <>₹6L<sup>+</sup></>, label: <>Average extra salary<br />negotiated per candidate</> },
  { value: "Free", label: <>For candidates —<br />forever, no asterisk</> },
];

const FOUNDER_STATS: { value: ReactNode; label: ReactNode }[] = [
  { value: <>8<sup>%</sup></>, label: <>Success fee — half what<br />agencies charge</> },
  { value: "3–5", label: <>Pre-qualified intros<br />per role per week</> },
  { value: <>90<sup>d</sup></>, label: <>Replacement guarantee<br />in writing, no fine print</> },
  { value: "24h", label: <>Time to activation<br />after you share the role</> },
];

export function Stats() {
  const { audience } = useAudience();
  const stats = audience === "candidate" ? CANDIDATE_STATS : FOUNDER_STATS;

  return (
    <section className="stats-sec" aria-label="Mitra by the numbers">
      <Reveal className="stats-row">
        {stats.map((s, i) => (
          <div className="stat-cell" key={i}>
            <div className="stat-n">{s.value}</div>
            <div className="stat-l">{s.label}</div>
          </div>
        ))}
      </Reveal>
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
