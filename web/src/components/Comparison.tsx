"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

type Cell = { kind: "yes"; note?: string } | { kind: "no"; note?: string } | { kind: "neutral"; note: string };
type Row = { attr: string; mitra: Cell; col2: Cell; col3: Cell; col4: Cell };

const CANDIDATE_ROWS: Row[] = [
  { attr: "Cost to you", mitra: { kind: "yes", note: "Free — forever" }, col2: { kind: "neutral", note: "Free but your time" }, col3: { kind: "no", note: "They work for the company" }, col4: { kind: "neutral", note: "Free but cold" } },
  { attr: "Response rate", mitra: { kind: "yes", note: "Warm intro, ~90%" }, col2: { kind: "no", note: "2–5% typical" }, col3: { kind: "neutral", note: "Varies by recruiter" }, col4: { kind: "no", note: "<1% cold DM" } },
  { attr: "Zero ghosting", mitra: { kind: "yes", note: "Guaranteed outcome" }, col2: { kind: "no" }, col3: { kind: "neutral", note: "Until placement only" }, col4: { kind: "no" } },
  { attr: "Salary negotiation coaching", mitra: { kind: "yes", note: "Counter-offer help included" }, col2: { kind: "no" }, col3: { kind: "no", note: "Works against you" }, col4: { kind: "no" } },
  { attr: "Match quality (why you, why them)", mitra: { kind: "yes", note: "Full context both ways" }, col2: { kind: "no", note: "Keyword filtered" }, col3: { kind: "neutral", note: "Varies widely" }, col4: { kind: "no", note: "None" } },
  { attr: "Someone advocates for you", mitra: { kind: "yes", note: "Personal introduction" }, col2: { kind: "no" }, col3: { kind: "neutral", note: "Limited" }, col4: { kind: "no" } },
  { attr: "Time to first response", mitra: { kind: "yes", note: "~8 days avg" }, col2: { kind: "no", note: "Weeks or never" }, col3: { kind: "neutral", note: "1–2 weeks" }, col4: { kind: "no", note: "Unpredictable" } },
];

const FOUNDER_ROWS: Row[] = [
  { attr: "Cost per hire", mitra: { kind: "yes", note: "Free for first 2 · 8% after" }, col2: { kind: "neutral", note: "Subscription + your time" }, col3: { kind: "no", note: "15–20% of CTC" }, col4: { kind: "neutral", note: "Salary + tooling + ads" } },
  { attr: "Time to first interview", mitra: { kind: "yes", note: "~8 days" }, col2: { kind: "no", note: "Weeks of screening" }, col3: { kind: "neutral", note: "1–3 weeks" }, col4: { kind: "no", note: "2–6 weeks" } },
  { attr: "Candidates per role", mitra: { kind: "yes", note: "3–5 pre-qualified" }, col2: { kind: "no", note: "Hundreds of applicants" }, col3: { kind: "neutral", note: "5–10 unscreened" }, col4: { kind: "no", note: "Whoever applies" } },
  { attr: "Match quality (motivation, fit)", mitra: { kind: "yes", note: "Full intent screen" }, col2: { kind: "no", note: "Keyword filtered" }, col3: { kind: "neutral", note: "Varies by recruiter" }, col4: { kind: "neutral", note: "Manual ATS filtering" } },
  { attr: "Replacement guarantee", mitra: { kind: "yes", note: "90 days" }, col2: { kind: "no" }, col3: { kind: "neutral", note: "60–90 days, varies" }, col4: { kind: "no" } },
  { attr: "Context on every candidate", mitra: { kind: "yes", note: "Salary, motivation, notice" }, col2: { kind: "no" }, col3: { kind: "neutral", note: "Sometimes" }, col4: { kind: "no" } },
  { attr: "Setup overhead", mitra: { kind: "yes", note: "WhatsApp · 24h" }, col2: { kind: "neutral", note: "Days" }, col3: { kind: "no", note: "Contract · 1–2 weeks" }, col4: { kind: "no", note: "Tooling · weeks" } },
];

const CANDIDATE_HEADERS = ["Mitra", "Job boards (Naukri / LinkedIn)", "Recruiters & agencies", "Cold networking / LinkedIn DMs"];
const FOUNDER_HEADERS = ["Mitra", "Job boards (Naukri / LinkedIn)", "Recruiters & agencies", "In-house hiring"];

const CANDIDATE_COPY = {
  headline: <>You deserve someone<br />in your <em>corner.</em></>,
  sub: "A side-by-side view of how candidates actually experience each channel in India today.",
};
const FOUNDER_COPY = {
  headline: <>You already know the alternatives.<br />Here&apos;s why they <em>don&apos;t work.</em></>,
  sub: "A side-by-side view of the four ways funded startups fill engineering and product roles in India in 2026.",
};

const Mark = ({ kind }: { kind: Cell["kind"] }) => {
  if (kind === "yes") return <span className="cmp-mark cmp-yes" aria-label="Yes">✓</span>;
  if (kind === "no") return <span className="cmp-mark cmp-no" aria-label="No">×</span>;
  return <span className="cmp-mark cmp-neutral" aria-label="Partial">◐</span>;
};

const CellView = ({ cell }: { cell: Cell }) => (
  <div className="cmp-cell-inner">
    <Mark kind={cell.kind} />
    {cell.note && <span className="cmp-note">{cell.note}</span>}
  </div>
);

export function Comparison() {
  const { audience } = useAudience();
  const rows = audience === "candidate" ? CANDIDATE_ROWS : FOUNDER_ROWS;
  const headers = audience === "candidate" ? CANDIDATE_HEADERS : FOUNDER_HEADERS;
  const copy = audience === "candidate" ? CANDIDATE_COPY : FOUNDER_COPY;

  return (
    <section className="cmp-sec" id="compare" aria-label="How Mitra compares">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">How we compare</div>
        <h2 className="sec-title sec-title--center">{copy.headline}</h2>
        <p className="sec-intro-desc sec-intro-desc--narrow">{copy.sub}</p>
      </Reveal>

      <Reveal delay={1}>
        <div className="cmp-desktop">
          <div className="cmp-table-wrap">
            <div className="cmp-table" role="table">
              <div className="cmp-row cmp-head" role="row">
                <div className="cmp-cell cmp-attr" role="columnheader">&nbsp;</div>
                <div className="cmp-cell cmp-col-mitra" role="columnheader"><span className="cmp-col-tag">Mitra</span></div>
                <div className="cmp-cell" role="columnheader">{headers[1]}</div>
                <div className="cmp-cell" role="columnheader">{headers[2]}</div>
                <div className="cmp-cell" role="columnheader">{headers[3]}</div>
              </div>
              {rows.map((row) => (
                <div className="cmp-row" key={row.attr} role="row">
                  <div className="cmp-cell cmp-attr" role="rowheader">{row.attr}</div>
                  <div className="cmp-cell cmp-col-mitra" role="cell"><CellView cell={row.mitra} /></div>
                  <div className="cmp-cell" role="cell"><CellView cell={row.col2} /></div>
                  <div className="cmp-cell" role="cell"><CellView cell={row.col3} /></div>
                  <div className="cmp-cell" role="cell"><CellView cell={row.col4} /></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="cmp-mobile">
          {rows.map((row) => (
            <article key={row.attr} className="cmp-m-card">
              <h3 className="cmp-m-title">{row.attr}</h3>
              <div className="cmp-m-grid">
                {([["Mitra", row.mitra, true], [headers[1], row.col2, false], [headers[2], row.col3, false], [headers[3], row.col4, false]] as [string, Cell, boolean][]).map(([label, cell, isMitra]) => (
                  <div key={label} className={`cmp-m-row${isMitra ? " cmp-m-row--mitra" : ""}`}>
                    <div className="cmp-m-channel">{label}</div>
                    <div className="cmp-m-cell"><CellView cell={cell} /></div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
