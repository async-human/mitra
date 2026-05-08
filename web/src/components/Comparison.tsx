import { Reveal } from "./Reveal";

type Cell =
  | { kind: "yes"; note?: string }
  | { kind: "no"; note?: string }
  | { kind: "neutral"; note: string };

type Row = {
  attr: string;
  mitra: Cell;
  jobBoards: Cell;
  recruiters: Cell;
  inHouse: Cell;
};

const ROWS: Row[] = [
  {
    attr: "Cost per hire",
    mitra: { kind: "yes", note: "Free for first 2 · 8% after" },
    jobBoards: { kind: "neutral", note: "Subscription + your time" },
    recruiters: { kind: "no", note: "15–20% of CTC" },
    inHouse: { kind: "neutral", note: "Salary + tooling + ads" },
  },
  {
    attr: "Time to first interview",
    mitra: { kind: "yes", note: "~8 days" },
    jobBoards: { kind: "no", note: "Weeks of screening" },
    recruiters: { kind: "neutral", note: "1–3 weeks" },
    inHouse: { kind: "no", note: "2–6 weeks" },
  },
  {
    attr: "Candidates per role",
    mitra: { kind: "yes", note: "3–5 pre-qualified" },
    jobBoards: { kind: "no", note: "Hundreds of applicants" },
    recruiters: { kind: "neutral", note: "5–10 unscreened" },
    inHouse: { kind: "no", note: "Whoever applies" },
  },
  {
    attr: "Match quality (motivation, fit)",
    mitra: { kind: "yes", note: "Full intent screen" },
    jobBoards: { kind: "no", note: "Keyword filtered" },
    recruiters: { kind: "neutral", note: "Varies by recruiter" },
    inHouse: { kind: "neutral", note: "Manual ATS filtering" },
  },
  {
    attr: "Replacement guarantee",
    mitra: { kind: "yes", note: "90 days" },
    jobBoards: { kind: "no" },
    recruiters: { kind: "neutral", note: "60–90 days, varies" },
    inHouse: { kind: "no" },
  },
  {
    attr: "Active for the candidate",
    mitra: { kind: "yes", note: "Negotiation + coaching" },
    jobBoards: { kind: "no" },
    recruiters: { kind: "neutral", note: "Until placement" },
    inHouse: { kind: "no" },
  },
  {
    attr: "Setup overhead",
    mitra: { kind: "yes", note: "WhatsApp · 24h" },
    jobBoards: { kind: "neutral", note: "Days" },
    recruiters: { kind: "no", note: "Contract · 1–2 weeks" },
    inHouse: { kind: "no", note: "Tooling · weeks" },
  },
];

const Mark = ({ kind }: { kind: Cell["kind"] }) => {
  if (kind === "yes")
    return (
      <span className="cmp-mark cmp-yes" aria-label="Yes">
        ✓
      </span>
    );
  if (kind === "no")
    return (
      <span className="cmp-mark cmp-no" aria-label="No">
        ×
      </span>
    );
  return (
    <span className="cmp-mark cmp-neutral" aria-label="Partial">
      ◐
    </span>
  );
};

const CellView = ({ cell }: { cell: Cell }) => (
  <div className="cmp-cell-inner">
    <Mark kind={cell.kind} />
    {cell.note && <span className="cmp-note">{cell.note}</span>}
  </div>
);

function MobileRow({
  label,
  cell,
  mitra,
}: {
  label: string;
  cell: Cell;
  mitra?: boolean;
}) {
  return (
    <div className={`cmp-m-row${mitra ? " cmp-m-row--mitra" : ""}`}>
      <div className="cmp-m-channel">{label}</div>
      <div className="cmp-m-cell">
        <CellView cell={cell} />
      </div>
    </div>
  );
}

export function Comparison() {
  return (
    <section className="cmp-sec" id="compare" aria-label="How Mitra compares">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">How we compare</div>
        <h2 className="sec-title sec-title--center">
          You already know <em>the alternatives.</em>
          <br />
          Here&apos;s why they don&apos;t work.
        </h2>
        <p className="sec-intro-desc sec-intro-desc--narrow">
          A side-by-side view of the four ways funded startups fill engineering
          and product roles in India in 2026. For{" "}
          <a href="#faq-replacement" className="sec-intro-inline-link">
            replacement terms
          </a>{" "}
          and pricing detail, see FAQ.
        </p>
      </Reveal>

      <Reveal delay={1}>
        <div className="cmp-desktop">
          <div className="cmp-table-wrap">
            <div className="cmp-table" role="table">
              <div className="cmp-row cmp-head" role="row">
                <div className="cmp-cell cmp-attr" role="columnheader">
                  &nbsp;
                </div>
                <div className="cmp-cell cmp-col-mitra" role="columnheader">
                  <span className="cmp-col-tag">Mitra</span>
                </div>
                <div className="cmp-cell" role="columnheader">
                  Job boards
                  <div className="cmp-sub">Naukri · LinkedIn</div>
                </div>
                <div className="cmp-cell" role="columnheader">
                  Recruiters
                  <div className="cmp-sub">Agencies</div>
                </div>
                <div className="cmp-cell" role="columnheader">
                  In-house
                  <div className="cmp-sub">Hire-yourself</div>
                </div>
              </div>

              {ROWS.map((row) => (
                <div className="cmp-row" key={row.attr} role="row">
                  <div className="cmp-cell cmp-attr" role="rowheader">
                    {row.attr}
                  </div>
                  <div className="cmp-cell cmp-col-mitra" role="cell">
                    <CellView cell={row.mitra} />
                  </div>
                  <div className="cmp-cell" role="cell">
                    <CellView cell={row.jobBoards} />
                  </div>
                  <div className="cmp-cell" role="cell">
                    <CellView cell={row.recruiters} />
                  </div>
                  <div className="cmp-cell" role="cell">
                    <CellView cell={row.inHouse} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="cmp-mobile">
          {ROWS.map((row) => (
            <article key={row.attr} className="cmp-m-card">
              <h3 className="cmp-m-title">{row.attr}</h3>
              <div className="cmp-m-grid">
                <MobileRow label="Mitra" cell={row.mitra} mitra />
                <MobileRow label="Job boards" cell={row.jobBoards} />
                <MobileRow label="Recruiters" cell={row.recruiters} />
                <MobileRow label="In-house" cell={row.inHouse} />
              </div>
            </article>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
