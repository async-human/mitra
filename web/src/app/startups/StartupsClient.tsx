"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
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
  return `$${usd}`;
}

function stageClass(stage: string | null): string {
  if (!stage) return s.stageDefault;
  const norm = stage.toLowerCase();
  if (norm.includes("seed") && !norm.includes("pre")) return s.stageSeed;
  if (norm.includes("pre"))   return s.stageDefault;
  if (norm.includes("series a")) return s.stageA;
  if (norm.includes("series b")) return s.stageB;
  if (norm.includes("series c")) return s.stageC;
  return s.stageLate;
}

function logoColor(name: string): string {
  const colors = [
    "#C8421A", "#1B5E5A", "#5E6AD2", "#A16207",
    "#166534", "#1E40AF", "#5B21B6", "#9D174D",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function isNew(createdAt: string): boolean {
  return Date.now() - new Date(createdAt).getTime() < 30 * 24 * 60 * 60 * 1000;
}

function CompanyCard({ company, index }: { company: CompanyFeedItem; index: number }) {
  const initial = company.name.charAt(0).toUpperCase();
  const color   = logoColor(company.name);
  const meta    = [company.sector, company.location].filter(Boolean).join(" · ");
  const fresh   = isNew(company.created_at);

  return (
    <article
      className={s.card}
      style={{ "--card-delay": `${Math.min(index * 0.04, 0.4)}s` } as React.CSSProperties}
    >
      {/* Top row */}
      <div className={s.cardTop}>
        <div className={s.cardLogo} style={{ background: color }}>
          {initial}
        </div>
        <div className={s.cardNameBlock}>
          <p className={s.cardName}>{company.name}</p>
          {meta && <p className={s.cardMeta}>{meta}</p>}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.35rem" }}>
          {company.stage && (
            <span className={`${s.stageBadge} ${stageClass(company.stage)}`}>
              {company.stage}
            </span>
          )}
          {fresh && <span className={s.newBadge}>New</span>}
        </div>
      </div>

      {/* Funding row */}
      {company.amount_usd ? (
        <div>
          <div className={s.cardFunding}>
            <span className={s.cardAmount}>{formatAmount(company.amount_usd)}</span>
            <span className={s.cardAmountLabel}>raised</span>
          </div>
          {company.investors.length > 0 && (
            <p className={s.cardInvestors}>
              <strong>{company.investors.slice(0, 3).join(" · ")}</strong>
            </p>
          )}
        </div>
      ) : company.investors.length > 0 ? (
        <p className={s.cardInvestors}>
          <strong>{company.investors.slice(0, 3).join(" · ")}</strong>
        </p>
      ) : null}

      {/* Founder */}
      {company.founder_name && (
        <div className={s.cardFounder}>
          <span className={s.cardFounderAv}>
            {company.founder_name.charAt(0).toUpperCase()}
          </span>
          {company.founder_name}
        </div>
      )}

      <div className={s.cardDivider} />

      {/* Footer */}
      <div className={s.cardFooter}>
        <div className={s.cardJobs}>
          {company.active_jobs > 0 ? (
            <>
              <span className={s.cardJobsNum}>{company.active_jobs}</span>
              {" "}open {company.active_jobs === 1 ? "role" : "roles"}
            </>
          ) : (
            <span className={s.cardJobsZero}>No open roles right now</span>
          )}
        </div>
        {company.board_url ? (
          <a
            href={company.board_url}
            target="_blank"
            rel="noopener noreferrer"
            className={s.cardCta}
          >
            View roles →
          </a>
        ) : (
          <span className={`${s.cardCta} ${s.cardCtaDisabled}`}>Coming soon</span>
        )}
      </div>
    </article>
  );
}

const ALL_STAGES  = ["Seed", "Series A", "Series B", "Series C", "Series D", "Series E", "Series F+"];
const ALL_SECTORS = ["Fintech", "B2B SaaS", "Consumer", "Developer Tools", "Healthtech", "Edtech", "Logistics"];

export function StartupsClient({ companies }: { companies: CompanyFeedItem[] }) {
  const [stageFilter,  setStageFilter]  = useState<string | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string | null>(null);

  const visibleStages = useMemo(() => {
    const set = new Set(companies.map((c) => c.stage).filter(Boolean) as string[]);
    return ALL_STAGES.filter((s) => set.has(s));
  }, [companies]);

  const visibleSectors = useMemo(() => {
    const set = new Set(companies.map((c) => c.sector).filter(Boolean) as string[]);
    return ALL_SECTORS.filter((s) => set.has(s));
  }, [companies]);

  const filtered = useMemo(() => {
    return companies.filter((c) => {
      if (stageFilter  && c.stage  !== stageFilter)  return false;
      if (sectorFilter && c.sector !== sectorFilter) return false;
      return true;
    });
  }, [companies, stageFilter, sectorFilter]);

  const totalJobs = companies.reduce((n, c) => n + c.active_jobs, 0);

  return (
    <>
      <header className={s.header}>
        <p className={s.headerEyebrow}>Funded &amp; Hiring</p>
        <h1 className={s.headerTitle}>
          India&rsquo;s best startups<br />
          <em>hiring right now</em>
        </h1>
        <p className={s.headerSub}>
          {companies.length} funded companies · {totalJobs} open roles across India
        </p>
        <div className={s.headerMeta}>
          <span className={s.metaPill}>
            <span className={s.metaDot} aria-hidden="true" />
            Updated daily
          </span>
          <span className={s.metaPill}>Series A through IPO</span>
          <span className={s.metaPill}>India only</span>
        </div>
      </header>

      {(visibleStages.length > 0 || visibleSectors.length > 0) && (
        <div className={s.filters} role="navigation" aria-label="Filter companies">
          <div className={s.filtersInner}>
            {visibleStages.length > 0 && (
              <div className={s.filterGroup} role="group" aria-label="Stage">
                <button
                  type="button"
                  className={`${s.filterBtn} ${stageFilter === null ? s.filterBtnActive : ""}`}
                  onClick={() => setStageFilter(null)}
                >
                  All stages
                </button>
                {visibleStages.map((stage) => (
                  <button
                    key={stage}
                    type="button"
                    className={`${s.filterBtn} ${stageFilter === stage ? s.filterBtnActive : ""}`}
                    onClick={() => setStageFilter(stageFilter === stage ? null : stage)}
                  >
                    {stage}
                  </button>
                ))}
              </div>
            )}

            {visibleStages.length > 0 && visibleSectors.length > 0 && (
              <div className={s.filterDivider} aria-hidden="true" />
            )}

            {visibleSectors.length > 0 && (
              <div className={s.filterGroup} role="group" aria-label="Sector">
                {visibleSectors.map((sector) => (
                  <button
                    key={sector}
                    type="button"
                    className={`${s.filterBtn} ${sectorFilter === sector ? s.filterBtnActive : ""}`}
                    onClick={() => setSectorFilter(sectorFilter === sector ? null : sector)}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <main className={s.main}>
        <div className={s.grid}>
          {filtered.length > 0 ? (
            filtered.map((company, i) => (
              <CompanyCard key={company.id} company={company} index={i} />
            ))
          ) : (
            <p className={s.empty}>No companies match this filter.</p>
          )}
        </div>
      </main>
    </>
  );
}
