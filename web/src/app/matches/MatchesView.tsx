"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/Logo";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface BasicCard { id: string; title: string; description: string; }
interface FullJob {
  id: number; title: string; company: string;
  stage: string | null; sector: string | null;
  location: string | null; remote_policy: string | null;
  employment: string | null;
  salary_min_lpa: number | null; salary_max_lpa: number | null;
  stack: string[]; summary: string | null;
  signals: Record<string, string>;
}
interface MergedJob extends FullJob {
  fit: string; fit_pct: number;
}

function parseFit(description: string): { fit: string; fit_pct: number } {
  const parts = description.split(" · ");
  const fitPart = parts.find(p => p.includes("% fit") || p.includes("%fit")) ?? "";
  const num = parseInt(fitPart.replace(/\D/g, "")) || 0;
  return { fit: fitPart, fit_pct: num };
}

function basicToMerged(cards: BasicCard[]): MergedJob[] {
  return cards.map((b, i) => {
    const { fit, fit_pct } = parseFit(b.description);
    const parts = b.description.split(" · ").map(s => s.trim()).filter(Boolean);
    const fitIdx = parts.findIndex(p => p.includes("% fit") || p.includes("%fit"));
    const company = fitIdx > 0 ? parts[0] : fitIdx === 0 ? "" : (parts[0] ?? "");
    // Remaining parts (not company, not fit%) become the stack/tag display
    const extra = parts.filter((_, j) => j !== 0 && j !== fitIdx);
    return {
      id: i + 1,
      title: b.title, company,
      stage: null, sector: null, location: null, remote_policy: null,
      employment: null, salary_min_lpa: null, salary_max_lpa: null,
      stack: extra, summary: null, signals: {}, fit, fit_pct,
    };
  });
}

function fitColor(pct: number) {
  if (pct >= 90) return "match-fit--high";
  if (pct >= 80) return "match-fit--mid";
  return "match-fit--low";
}

function salaryLabel(min: number | null, max: number | null) {
  if (!min && !max) return null;
  if (min && max) return `₹${min}–${max}L`;
  if (min) return `₹${min}L+`;
  return `up to ₹${max}L`;
}

function remoteLabel(policy: string | null) {
  if (!policy) return null;
  const m: Record<string, string> = { remote: "Remote", hybrid: "Hybrid", onsite: "On-site" };
  return m[policy.toLowerCase()] ?? policy;
}

function employmentLabel(e: string | null) {
  if (!e) return null;
  return e === "full_time" ? "Full-time" : e === "contract" ? "Contract" : e;
}

function StarRating({ pct }: { pct: number }) {
  const filled = pct >= 95 ? 5 : pct >= 88 ? 4 : pct >= 78 ? 3 : pct >= 65 ? 2 : 1;
  return (
    <span className="match-stars" aria-label={`${filled} of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < filled ? "match-star match-star--on" : "match-star"}>★</span>
      ))}
    </span>
  );
}

function JobCard({ job, idx }: { job: MergedJob; idx: number }) {
  const salary = salaryLabel(job.salary_min_lpa, job.salary_max_lpa);
  const remote = remoteLabel(job.remote_policy);
  const empType = employmentLabel(job.employment);
  const pills = [job.stage, job.sector, remote, empType, salary].filter(Boolean) as string[];

  return (
    <div className="match-card" style={{ animationDelay: `${idx * 0.07}s` }}>
      {/* Card header */}
      <div className="match-card-header">
        <div className="match-company-av">
          {job.company.slice(0, 2).toUpperCase()}
        </div>
        <div className="match-card-meta">
          <h2 className="match-role">{job.title}</h2>
          <p className="match-company">{job.company}</p>
        </div>
        {job.fit && (
          <div className={`match-fit ${fitColor(job.fit_pct)}`}>
            <span className="match-fit-pct">{job.fit_pct}%</span>
            <span className="match-fit-label">fit</span>
          </div>
        )}
      </div>

      {/* Stars */}
      {job.fit_pct > 0 && (
        <div className="match-stars-row">
          <StarRating pct={job.fit_pct} />
        </div>
      )}

      {/* Pills row */}
      {pills.length > 0 && (
        <div className="match-pills">
          {pills.map((p, i) => <span key={i} className="match-pill">{p}</span>)}
        </div>
      )}

      {/* Divider */}
      <div className="match-divider" />

      {/* Summary */}
      {job.summary && (
        <p className="match-summary">{job.summary}</p>
      )}

      {/* Stack */}
      {job.stack.length > 0 && (
        <div className="match-stack">
          {job.stack.map((s, i) => <span key={i} className="match-stack-tag">{s}</span>)}
        </div>
      )}

      {/* Actions */}
      <div className="match-actions">
        <Link href={`/chat?about=${encodeURIComponent(job.title)}`} className="match-btn match-btn--ghost">
          Ask Mitra →
        </Link>
        <Link href="/chat" className="match-btn match-btn--primary">
          Request intro
        </Link>
      </div>
    </div>
  );
}

export function MatchesView({ userName, urlIds }: { userName?: string; urlIds?: string }) {
  const [jobs, setJobs] = useState<MergedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const firstName = userName?.split(" ")[0];

  useEffect(() => {
    async function load() {
      // sessionStorage has rich data (fit%, description). URL params are the fallback.
      const raw = sessionStorage.getItem("mitra-matches");
      let basic: BasicCard[] | null = null;
      if (raw) {
        try { basic = JSON.parse(raw); } catch { basic = null; }
      }

      // Determine which IDs to fetch
      let ids: string;
      if (basic && basic.length > 0) {
        ids = basic.map(c => c.id.replace(/^job_/, "")).join(",");
      } else if (urlIds) {
        ids = urlIds.split(",").map(s => s.trim().replace(/^job_/, "")).join(",");
      } else {
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_URL}/candidate/jobs?ids=${ids}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const full: FullJob[] = await res.json();
        if (full.length > 0) {
          // Full DB enrichment succeeded — merge fit% from basic card descriptions
          const merged = full.map(f => {
            const b = basic?.find(c => Number(c.id.replace(/^job_/, "")) === f.id);
            const { fit, fit_pct } = parseFit(b?.description ?? "");
            return { ...f, fit, fit_pct };
          });
          setJobs(merged);
        } else if (basic && basic.length > 0) {
          // Backend returned empty (IDs are non-integer vector store IDs) — show basic cards
          setJobs(basicToMerged(basic));
        }
      } catch {
        if (basic && basic.length > 0) {
          setJobs(basicToMerged(basic));
        }
      }
      setLoading(false);
    }
    load();
  }, [urlIds]);

  return (
    <div className="match-root">
      <header className="match-topbar">
        <Logo />
        <nav className="match-topbar-nav">
          <Link href="/chat" className="match-nav-link">← Back to chat</Link>
          <Link href="/dashboard" className="match-nav-link">Dashboard</Link>
        </nav>
      </header>

      <main className="match-main">
        <div className="match-heading">
          <p className="match-eyebrow">Your shortlist</p>
          <h1 className="match-title">
            {firstName ? `${firstName}'s matches` : "Your matches"}
          </h1>
          {jobs.length > 0 && (
            <p className="match-sub">
              {jobs.length} role{jobs.length !== 1 ? "s" : ""} curated for you · ranked by fit
            </p>
          )}
        </div>

        {loading ? (
          <div className="match-loading">
            <div className="match-spinner" />
            <p>Loading your matches…</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="match-empty">
            <p className="match-empty-title">No matches yet</p>
            <p className="match-empty-sub">
              Chat with Mitra to get your personalised shortlist.
            </p>
            <Link href="/chat" className="match-btn match-btn--primary">Start the conversation →</Link>
          </div>
        ) : (
          <div className="match-grid">
            {jobs.map((job, i) => <JobCard key={`${job.id}-${i}`} job={job} idx={i} />)}
          </div>
        )}
      </main>
    </div>
  );
}
