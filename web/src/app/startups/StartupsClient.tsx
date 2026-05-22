"use client";

import { useState, useMemo } from "react";
import s from "./startups.module.css";

export interface CompanyFeedItem {
  id: number;
  name: string;
  stage: string | null;
  sector: string | null;
  location: string | null;
  website: string | null;
  founder_name: string | null;
  amount_usd: number | null;
  investors: string[];
  active_jobs: number;
  board_url: string | null;
  created_at: string;
}

function formatAmount(usd: number): string {
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000)     return `$${Math.round(usd / 1_000_000)}M`;
  if (usd >= 1_000)         return `$${Math.round(usd / 1_000)}K`;
  return `$${usd.toLocaleString()}`;
}

function stageCls(stage: string | null): string {
  if (!stage) return s.stageDefault;
  const n = stage.toLowerCase();
  if (n === "seed")       return s.stageSeed;
  if (n === "series a")   return s.stageA;
  if (n === "series b")   return s.stageB;
  if (n === "series c")   return s.stageC;
  if (n.startsWith("pre")) return s.stageDefault;
  return s.stageLate;
}

function CompanyCard({ company, index }: { company: CompanyFeedItem; index: number }) {
  const meta = [company.sector, company.location].filter(Boolean).join(" · ");

  return (
    <article
      className={s.card}
      style={{ "--card-delay": `${Math.min(index * 0.045, 0.45)}s` } as React.CSSProperties}
    >
      {/* Identity */}
      <div className={s.cardHead}>
        <div className={s.cardInitial}>
          {company.name.charAt(0).toUpperCase()}
        </div>
        <div className={s.cardIdentity}>
          <p className={s.cardName}>{company.name}</p>
          {meta && <p className={s.cardMeta}>{meta}</p>}
        </div>
        {company.stage && (
          <span className={`${s.stagePill} ${stageCls(company.stage)}`}>
            {company.stage}
          </span>
        )}
      </div>

      {/* Funding */}
      <div className={s.cardFundingBlock}>
        {company.amount_usd ? (
          <>
            <div className={s.cardAmount}>{formatAmount(company.amount_usd)}</div>
            <div className={s.cardAmountNote}>Raised</div>
            {company.investors.length > 0 && (
              <p className={s.cardInvestors}>
                {company.investors.slice(0, 3).join(" · ")}
              </p>
            )}
          </>
        ) : (
          <>
            <p className={s.cardUndisclosed}>Amount undisclosed</p>
            {company.investors.length > 0 && (
              <p className={s.cardInvestors} style={{ marginTop: "0.35rem" }}>
                {company.investors.slice(0, 3).join(" · ")}
              </p>
            )}
          </>
        )}
      </div>

      {/* Founder */}
      {company.founder_name && (
        <div className={s.cardFounder}>
          <span className={s.cardFounderDot} aria-hidden="true" />
          {company.founder_name}
        </div>
      )}

      {/* Footer */}
      <div className={s.cardFooter}>
        <span className={s.cardJobCount}>
          {company.active_jobs > 0 ? (
            <>
              <span className={s.cardJobNum}>{company.active_jobs}</span>
              {" "}open {company.active_jobs === 1 ? "role" : "roles"}
            </>
          ) : (
            "No open roles"
          )}
        </span>
        {company.board_url ? (
          <a
            href={company.board_url}
            target="_blank"
            rel="noopener noreferrer"
            className={s.cardLink}
          >
            View roles →
          </a>
        ) : (
          <span className={s.cardLinkNone}>Board not listed</span>
        )}
      </div>
    </article>
  );
}

const STAGE_ORDER  = ["Seed", "Series A", "Series B", "Series C", "Series D", "Series E", "Series F", "Growth", "IPO"];
const SECTOR_ORDER = ["Fintech", "B2B SaaS", "Consumer", "Developer Tools", "AI / SaaS", "Healthtech", "Edtech", "Logistics", "Mobility", "Infrastructure / DevOps", "Design Tools"];

export function StartupsClient({ companies }: { companies: CompanyFeedItem[] }) {
  const [stageFilter,  setStageFilter]  = useState<string | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string | null>(null);

  const presentStages = useMemo(() => {
    const present = new Set(companies.map((c) => c.stage).filter(Boolean) as string[]);
    return STAGE_ORDER.filter((st) => present.has(st));
  }, [companies]);

  const presentSectors = useMemo(() => {
    const present = new Set(companies.map((c) => c.sector).filter(Boolean) as string[]);
    return SECTOR_ORDER.filter((se) => present.has(se));
  }, [companies]);

  const filtered = useMemo(() => companies.filter((c) => {
    if (stageFilter  && c.stage  !== stageFilter)  return false;
    if (sectorFilter && c.sector !== sectorFilter) return false;
    return true;
  }), [companies, stageFilter, sectorFilter]);

  const totalJobs = companies.reduce((n, c) => n + c.active_jobs, 0);

  return (
    <>
      <header className={s.header}>
        <div className={s.headerRule}>
          <span className={s.headerRuleDot} aria-hidden="true" />
          <span className={s.headerRuleLabel}>Funded &amp; Hiring</span>
        </div>
        <h1 className={s.headerTitle}>
          India&rsquo;s best-funded<br />
          <em>startups, hiring now</em>
        </h1>
        <div className={s.headerStats}>
          <div className={s.headerStat}>
            <span className={s.headerStatNum}>{companies.length}</span>
            <span className={s.headerStatLabel}>Companies</span>
          </div>
          <div className={s.headerStatDiv} />
          <div className={s.headerStat}>
            <span className={s.headerStatNum}>{totalJobs}</span>
            <span className={s.headerStatLabel}>Open roles</span>
          </div>
          <div className={s.headerStatDiv} />
          <div className={s.headerStat}>
            <span className={s.headerStatNum}>{presentStages.length}</span>
            <span className={s.headerStatLabel}>Funding stages</span>
          </div>
        </div>
      </header>

      {(presentStages.length > 0 || presentSectors.length > 0) && (
        <nav className={s.filters} aria-label="Filter companies">
          <div className={s.filtersInner}>
            <span className={s.filterLabel}>Filter</span>
            <button
              type="button"
              className={`${s.filterBtn} ${stageFilter === null && sectorFilter === null ? s.filterBtnActive : ""}`}
              onClick={() => { setStageFilter(null); setSectorFilter(null); }}
            >
              All
            </button>

            {presentStages.length > 0 && (
              <>
                <div className={s.filterSep} aria-hidden="true" />
                {presentStages.map((st) => (
                  <button
                    key={st}
                    type="button"
                    className={`${s.filterBtn} ${stageFilter === st ? s.filterBtnActive : ""}`}
                    onClick={() => { setStageFilter(stageFilter === st ? null : st); setSectorFilter(null); }}
                  >
                    {st}
                  </button>
                ))}
              </>
            )}

            {presentSectors.length > 0 && (
              <>
                <div className={s.filterSep} aria-hidden="true" />
                {presentSectors.map((se) => (
                  <button
                    key={se}
                    type="button"
                    className={`${s.filterBtn} ${sectorFilter === se ? s.filterBtnActive : ""}`}
                    onClick={() => { setSectorFilter(sectorFilter === se ? null : se); setStageFilter(null); }}
                  >
                    {se}
                  </button>
                ))}
              </>
            )}
          </div>
        </nav>
      )}

      <main className={s.main}>
        <div className={s.grid}>
          {filtered.length > 0 ? (
            filtered.map((c, i) => <CompanyCard key={c.id} company={c} index={i} />)
          ) : (
            <p className={s.empty}>No companies match this filter.</p>
          )}
        </div>
      </main>
    </>
  );
}
