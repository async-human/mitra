import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

const STATS: { value: ReactNode; label: ReactNode }[] = [
  {
    value: (
      <>
        8<sup>d</sup>
      </>
    ),
    label: (
      <>
        Average days to first
        <br />
        interview after intro
      </>
    ),
  },
  {
    value: "0",
    label: (
      <>
        Candidates ghosted —
        <br />
        our iron promise
      </>
    ),
  },
  {
    value: (
      <>
        8<sup>%</sup>
      </>
    ),
    label: (
      <>
        Success fee — half what
        <br />
        agencies charge
      </>
    ),
  },
  {
    value: "Free",
    label: (
      <>
        For candidates —
        <br />
        forever, no asterisk
      </>
    ),
  },
];

export function Stats() {
  return (
    <section className="stats-sec" aria-label="Mitra by the numbers">
      <Reveal className="stats-row">
        {STATS.map((s, i) => (
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
          <strong>not audited metrics</strong>. &ldquo;Zero ghosting&rdquo;
          means we stay in your corner until there is a clear outcome — ask us
          how that works in practice on WhatsApp.
        </p>
      </Reveal>
    </section>
  );
}
