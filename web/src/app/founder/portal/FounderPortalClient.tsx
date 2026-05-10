"use client";

import React, { useEffect, useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PortalSignals {
  name: string | null;
  current_role: string | null;
  current_company: string | null;
  years_exp: number | null;
  stack: string[];
  salary_target_lpa: number | null;
  notice_period_days: number | null;
  motivation: string | null;
  notable_projects: string | null;
  linkedin_url: string | null;
}

interface PortalCandidate {
  intro_id: number;
  status: string;
  sent_at: string | null;
  why_note: string | null;
  signals: PortalSignals;
}

interface PortalJob {
  id: number;
  title: string;
  company: string;
  stage: string | null;
  sector: string | null;
  location: string | null;
  remote_policy: string | null;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  stack: string[];
  summary: string | null;
}

interface PortalStats {
  total: number;
  interested: number;
  interview: number;
  offer: number;
  hired: number;
  declined: number;
}

interface PortalData {
  job: PortalJob;
  candidates: PortalCandidate[];
  stats: PortalStats;
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  sent:         { label: "New introduction", color: "#0F766E", bg: "#F0FDFA", dot: "#2DD4BF" },
  acknowledged: { label: "Interested",       color: "#6D28D9", bg: "#F5F3FF", dot: "#8B5CF6" },
  interview:    { label: "Interview set",    color: "#B45309", bg: "#FFFBEB", dot: "#F59E0B" },
  offer:        { label: "Offer extended",   color: "#1D4ED8", bg: "#EFF6FF", dot: "#60A5FA" },
  hired:        { label: "Hired",            color: "#065F46", bg: "#ECFDF5", dot: "#34D399" },
  declined:     { label: "Not a fit",        color: "#6B7280", bg: "#F9FAFB", dot: "#D1D5DB" },
  ghosted:      { label: "Awaiting reply",   color: "#9CA3AF", bg: "#F9FAFB", dot: "#E5E7EB" },
};
function statusMeta(s: string) {
  return STATUS[s] ?? { label: s, color: "#6B7280", bg: "#F9FAFB", dot: "#D1D5DB" };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function initials(name: string | null, role: string | null): string {
  const n = (name || role || "??").trim();
  const parts = n.split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : n.slice(0, 2).toUpperCase();
}

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/** Convert *bold* / **bold** markdown to <strong> for inline rendering. */
function renderMarkdown(text: string): React.ReactNode[] {
  return text.split(/(\*{1,2}[^*]+\*{1,2})/g).map((chunk, i) => {
    if (/^\*{1,2}.+\*{1,2}$/.test(chunk)) {
      const inner = chunk.replace(/^\*{1,2}/, "").replace(/\*{1,2}$/, "");
      return <strong key={i} style={{ fontWeight: 700, color: "inherit" }}>{inner}</strong>;
    }
    return chunk;
  });
}

/**
 * Split a raw summary string on ` | ` separators and render as a clean
 * two-column fact grid (label: value pairs separated by ": ").
 */
function JobSummary({ text }: { text: string }) {
  const parts = text.split(/\s*\|\s*/).map(s => s.trim()).filter(Boolean);
  if (parts.length <= 1) {
    return <p className="fp2-job-summary">{text}</p>;
  }
  return (
    <ul className="fp2-job-summary-list">
      {parts.map((part, i) => {
        const colon = part.indexOf(": ");
        if (colon > 0) {
          return (
            <li key={i} className="fp2-job-summary-item">
              <span className="fp2-job-summary-key">{part.slice(0, colon)}</span>
              <span className="fp2-job-summary-val">{part.slice(colon + 2)}</span>
            </li>
          );
        }
        return <li key={i} className="fp2-job-summary-item fp2-job-summary-item--plain">{part}</li>;
      })}
    </ul>
  );
}

function salaryLabel(min: number | null, max: number | null) {
  if (!min && !max) return null;
  if (min && max && min !== max) return `₹${min}–${max}L`;
  return `₹${min || max}L`;
}

const AVATAR_PALETTES = [
  { bg: "#EDE9FE", fg: "#5B21B6" },
  { bg: "#DBEAFE", fg: "#1E40AF" },
  { bg: "#D1FAE5", fg: "#065F46" },
  { bg: "#FEF3C7", fg: "#92400E" },
  { bg: "#FCE7F3", fg: "#9D174D" },
  { bg: "#E0F2FE", fg: "#075985" },
];
function avatarPalette(idx: number) { return AVATAR_PALETTES[idx % AVATAR_PALETTES.length]; }

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconCheck() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path d="M3 7.5L6.5 11L12 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconCalendar() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <rect x="1.5" y="2.5" width="11" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1.5 6h11M5 1v3M9 1v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M2 2L11 11M11 2L2 11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function IconStar() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 1l1.545 3.13 3.455.502-2.5 2.436.59 3.44L7 8.885l-3.09 1.623.59-3.44L2 4.632l3.455-.502L7 1z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

// ── Candidate card ────────────────────────────────────────────────────────────

function CandidateCard({
  candidate, idx, token, onStatusChange,
}: {
  candidate: PortalCandidate;
  idx: number;
  token: string;
  onStatusChange: (introId: number, newStatus: string) => void;
}) {
  const s = candidate.signals;
  const meta = statusMeta(candidate.status);
  const palette = avatarPalette(idx);
  const [actionState, setActionState] = useState<"idle" | "loading" | "done">("idle");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const isActioned = ["acknowledged", "interview", "declined", "hired", "offer"].includes(candidate.status);

  const doAction = useCallback(async (action: string) => {
    setActionState("loading");
    try {
      const res = await fetch(`${API_URL}/founder/portal/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, intro_id: candidate.intro_id, action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed");
      setToast({ msg: data.message, ok: true });
      setActionState("done");
      onStatusChange(candidate.intro_id, data.new_status);
    } catch (e: unknown) {
      setActionState("idle");
      setToast({ msg: e instanceof Error ? e.message : "Something went wrong", ok: false });
    }
    setTimeout(() => setToast(null), 4000);
  }, [token, candidate.intro_id, onStatusChange]);

  return (
    <article className="fpc" style={{ "--fpc-delay": `${idx * 0.07}s` } as React.CSSProperties}>

      {/* Header */}
      <div className="fpc-header">
        <div className="fpc-av" style={{ background: palette.bg, color: palette.fg }}>
          {initials(s.name, s.current_role)}
        </div>

        <div className="fpc-identity">
          <h3 className="fpc-name">{s.name || "Anonymous Candidate"}</h3>
          <p className="fpc-role">
            {[s.current_role, s.current_company].filter(Boolean).join(" · ") || "Engineer"}
          </p>
          {candidate.sent_at && (
            <p className="fpc-date">Introduced {formatDate(candidate.sent_at)}</p>
          )}
        </div>

        <span className="fpc-status" style={{ color: meta.color, background: meta.bg }}>
          <span className="fpc-status-dot" style={{ background: meta.dot }} />
          {meta.label}
        </span>
      </div>

      {/* Quick stats row */}
      <div className="fpc-meta-row">
        {s.years_exp != null && (
          <span className="fpc-meta-chip">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.3" />
              <path d="M6 4v2.5l1.5 1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            {s.years_exp}y exp
          </span>
        )}
        {s.salary_target_lpa != null && (
          <span className="fpc-meta-chip">
            <span style={{ fontSize: 11 }}>₹</span>
            {s.salary_target_lpa}L target
          </span>
        )}
        {s.notice_period_days != null && (
          <span className="fpc-meta-chip">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <rect x="1" y="2" width="10" height="9" rx="2" stroke="currentColor" strokeWidth="1.2" />
              <path d="M1 5h10M4 1v2M8 1v2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            {s.notice_period_days}d notice
          </span>
        )}
      </div>

      {/* Stack tags */}
      {s.stack.length > 0 && (
        <div className="fpc-stack">
          {s.stack.slice(0, 7).map((t, i) => (
            <span key={i} className="fpc-tag">{t}</span>
          ))}
        </div>
      )}

      {/* Why Mitra matched */}
      {candidate.why_note && (
        <div className="fpc-why">
          <div className="fpc-why-label">
            <IconStar />
            Why Mitra matched them
          </div>
          <p className="fpc-why-text">{renderMarkdown(candidate.why_note)}</p>
        </div>
      )}

      {/* Motivation & projects */}
      {(s.motivation || s.notable_projects) && (
        <div className="fpc-extras">
          {s.motivation && (
            <div className="fpc-extra-item">
              <span className="fpc-extra-label">Looking for</span>
              <span className="fpc-extra-value">{s.motivation}</span>
            </div>
          )}
          {s.notable_projects && (
            <div className="fpc-extra-item">
              <span className="fpc-extra-label">Built</span>
              <span className="fpc-extra-value">{s.notable_projects}</span>
            </div>
          )}
        </div>
      )}

      {/* Toast notification */}
      {toast && (
        <div className={`fpc-toast ${toast.ok ? "fpc-toast--ok" : "fpc-toast--err"}`}>
          {toast.msg}
        </div>
      )}

      {/* Actions */}
      {!isActioned ? (
        <div className="fpc-actions">
          <button
            className="fpc-btn fpc-btn--primary"
            disabled={actionState === "loading"}
            onClick={() => doAction("interested")}
          >
            {actionState === "loading"
              ? <span className="fpc-spinner" />
              : <IconCheck />
            }
            Interested
          </button>
          <button
            className="fpc-btn fpc-btn--schedule"
            disabled={actionState === "loading"}
            onClick={() => doAction("schedule")}
          >
            <IconCalendar />
            Schedule interview
          </button>
          <button
            className="fpc-btn fpc-btn--pass"
            disabled={actionState === "loading"}
            onClick={() => doAction("not_a_fit")}
          >
            <IconX />
            Pass
          </button>
        </div>
      ) : (
        <div className="fpc-actioned" style={{ borderColor: meta.dot, color: meta.color }}>
          <span className="fpc-actioned-dot" style={{ background: meta.dot }} />
          <span>{meta.label}</span>
          {candidate.status !== "declined" && (
            <span className="fpc-actioned-note">· candidate notified</span>
          )}
        </div>
      )}
    </article>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: PortalStats }) {
  const items = [
    { value: stats.total,      label: "Introduced",   accent: "var(--fp-text-1)" },
    { value: stats.interested, label: "Interested",   accent: "#7C3AED" },
    { value: stats.interview,  label: "Interviewing", accent: "#D97706" },
    { value: stats.offer,      label: "Offer",        accent: "#2563EB" },
    { value: stats.hired,      label: "Hired",        accent: "#059669" },
  ];
  return (
    <div className="fp-statsbar">
      {items.map((item, i) => (
        <React.Fragment key={item.label}>
          {i > 0 && <div className="fp-statsbar-sep" />}
          <div className="fp-statsbar-item">
            <span className="fp-statsbar-num" style={{ color: item.accent }}>{item.value}</span>
            <span className="fp-statsbar-label">{item.label}</span>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

const FILTERS = [
  { key: "all",          label: "All" },
  { key: "sent",         label: "New" },
  { key: "acknowledged", label: "Interested" },
  { key: "interview",    label: "Interview" },
  { key: "offer",        label: "Offer" },
  { key: "declined",     label: "Declined" },
];

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="fp-empty">
      <div className="fp-empty-ring">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
          <circle cx="20" cy="20" r="14" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
          <path d="M20 14v6.5l4 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="fp-empty-title">No candidates yet</p>
      <p className="fp-empty-sub">Mitra is actively searching. You&apos;ll be notified as soon as there&apos;s a strong match.</p>
    </div>
  );
}

// ── Main portal ───────────────────────────────────────────────────────────────

export function FounderPortalClient({ token }: { token: string }) {
  const [data, setData]       = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string>("");
  const [filter, setFilter]   = useState("all");

  useEffect(() => {
    if (!token) { setError("No portal token provided."); setLoading(false); return; }
    fetch(`${API_URL}/founder/portal?token=${encodeURIComponent(token)}`)
      .then(r => { if (!r.ok) throw new Error("Portal not found or token expired."); return r.json(); })
      .then((d: PortalData) => { setData(d); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [token]);

  const handleStatusChange = useCallback((introId: number, newStatus: string) => {
    setData(prev => {
      if (!prev) return prev;
      const updated = prev.candidates.map(c =>
        c.intro_id === introId ? { ...c, status: newStatus } : c
      );
      return {
        ...prev,
        candidates: updated,
        stats: {
          ...prev.stats,
          interested: updated.filter(c => c.status === "acknowledged").length,
          interview:  updated.filter(c => c.status === "interview").length,
          offer:      updated.filter(c => c.status === "offer").length,
        },
      };
    });
  }, []);

  if (loading) return <PortalSkeleton />;
  if (error || !data) return <PortalError message={error || "Something went wrong."} />;

  const { job, candidates, stats } = data;

  const counts: Record<string, number> = {};
  for (const c of candidates) counts[c.status] = (counts[c.status] ?? 0) + 1;
  const filtered = filter === "all" ? candidates : candidates.filter(c => c.status === filter);

  const salaryStr = salaryLabel(job.salary_min_lpa, job.salary_max_lpa);

  return (
    <div className="fp2-root">
      {/* Top bar */}
      <header className="fp2-topbar">
        <span className="fp2-logo">Mitra<span className="fp2-logo-dot">.</span></span>
        <span className="fp2-topbar-pill">Founder Portal</span>
      </header>

      <main className="fp2-main">
        {/* Job card */}
        <section className="fp2-job-card">
          <div className="fp2-job-av">
            {job.company.slice(0, 2).toUpperCase()}
          </div>
          <div className="fp2-job-body">
            <div className="fp2-job-top">
              <div>
                <h1 className="fp2-job-title">{job.title}</h1>
                <p className="fp2-job-company">{job.company}</p>
              </div>
              {job.stage && <span className="fp2-job-stage">{job.stage}</span>}
            </div>

            <div className="fp2-job-badges">
              {/* Show location only when it's not just a repeat of remote_policy */}
              {job.location && job.location.toLowerCase() !== (job.remote_policy ?? "") && (
                <span className="fp2-job-badge">
                  <svg width="11" height="13" viewBox="0 0 11 13" fill="none" aria-hidden="true">
                    <path d="M5.5 1C3.015 1 1 3.015 1 5.5c0 3.375 4.5 7 4.5 7s4.5-3.625 4.5-7C10 3.015 7.985 1 5.5 1Z" stroke="currentColor" strokeWidth="1.3" />
                    <circle cx="5.5" cy="5.5" r="1.5" stroke="currentColor" strokeWidth="1.2" />
                  </svg>
                  {job.location}
                </span>
              )}
              {job.remote_policy && (
                <span className="fp2-job-badge">
                  {job.remote_policy === "remote" && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.2" />
                      <ellipse cx="6" cy="6" rx="2" ry="4.5" stroke="currentColor" strokeWidth="1.2" />
                      <path d="M1.5 6h9" stroke="currentColor" strokeWidth="1.2" />
                    </svg>
                  )}
                  {job.remote_policy.charAt(0).toUpperCase() + job.remote_policy.slice(1)}
                </span>
              )}
              {salaryStr && <span className="fp2-job-badge">{salaryStr} / yr</span>}
              {job.sector  && <span className="fp2-job-badge">{job.sector}</span>}
            </div>

            {job.summary && <JobSummary text={job.summary} />}
          </div>
        </section>

        {/* Stats */}
        <StatsBar stats={stats} />

        {/* Divider */}
        <div className="fp2-section-label">
          <span>Introductions</span>
          <span className="fp2-section-count">{candidates.length}</span>
        </div>

        {/* Filter tabs */}
        {candidates.length > 0 && (
          <div className="fp2-filters">
            {FILTERS.map(f => {
              const count = f.key === "all" ? candidates.length : (counts[f.key] ?? 0);
              if (f.key !== "all" && count === 0) return null;
              return (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`fp2-filter${filter === f.key ? " fp2-filter--on" : ""}`}
                >
                  {f.label}
                  {count > 0 && (
                    <span className={`fp2-filter-badge${filter === f.key ? " fp2-filter-badge--on" : ""}`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Candidate list */}
        <div className="fp2-list">
          {filtered.length === 0
            ? <EmptyState />
            : filtered.map((c, i) => (
              <CandidateCard
                key={c.intro_id}
                candidate={c}
                idx={i}
                token={token}
                onStatusChange={handleStatusChange}
              />
            ))
          }
        </div>

        <p className="fp2-footer">
          Introductions curated by Mitra — AI talent agent for India&apos;s funded startups.
        </p>
      </main>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function PortalSkeleton() {
  return (
    <div className="fp2-root">
      <header className="fp2-topbar">
        <span className="fp2-logo">Mitra<span className="fp2-logo-dot">.</span></span>
        <span className="fp2-topbar-pill">Founder Portal</span>
      </header>
      <main className="fp2-main">
        <section className="fp2-job-card">
          <div className="fp2-sk" style={{ width: 56, height: 56, borderRadius: 14, flexShrink: 0 }} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="fp2-sk" style={{ height: 22, width: "45%", borderRadius: 6 }} />
            <div className="fp2-sk" style={{ height: 14, width: "28%", borderRadius: 4 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
              {[72, 64, 80].map((w, i) => <div key={i} className="fp2-sk" style={{ height: 24, width: w, borderRadius: 20 }} />)}
            </div>
          </div>
        </section>
        <div className="fp-statsbar" style={{ marginTop: 0 }}>
          {[1,2,3,4,5].map(i => (
            <div key={i} className="fp-statsbar-item">
              <div className="fp2-sk" style={{ height: 26, width: 32, borderRadius: 5, marginBottom: 6 }} />
              <div className="fp2-sk" style={{ height: 11, width: 56, borderRadius: 4 }} />
            </div>
          ))}
        </div>
        <div className="fp2-list">
          {[0, 1, 2].map(i => (
            <div key={i} className="fpc fpc--sk" style={{ "--fpc-delay": `${i * 0.08}s` } as React.CSSProperties}>
              <div className="fpc-header">
                <div className="fp2-sk" style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0 }} />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                  <div className="fp2-sk" style={{ height: 15, width: "48%", borderRadius: 4 }} />
                  <div className="fp2-sk" style={{ height: 12, width: "32%", borderRadius: 4 }} />
                </div>
                <div className="fp2-sk" style={{ height: 24, width: 100, borderRadius: 20 }} />
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                {[55, 75, 65, 85].map((w, j) => (
                  <div key={j} className="fp2-sk" style={{ height: 25, width: w, borderRadius: 20 }} />
                ))}
              </div>
              <div className="fp2-sk" style={{ height: 72, borderRadius: 12, marginTop: 14 }} />
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                {[1, 2, 3].map(j => <div key={j} className="fp2-sk" style={{ height: 36, flex: j === 1 ? 1.4 : 1, borderRadius: 10 }} />)}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

// ── Error ─────────────────────────────────────────────────────────────────────

function PortalError({ message }: { message: string }) {
  return (
    <div className="fp2-error-page">
      <div className="fp2-error-card">
        <div className="fp2-error-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <path d="M14 3L26 24H2L14 3Z" stroke="#D97706" strokeWidth="1.6" strokeLinejoin="round" />
            <path d="M14 11v5" stroke="#D97706" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="14" cy="19.5" r="1" fill="#D97706" />
          </svg>
        </div>
        <h2 className="fp2-error-title">Portal unavailable</h2>
        <p className="fp2-error-desc">{message}</p>
        <p className="fp2-error-hint">
          If you received this link via email, it may have expired.<br />
          Reply to the original intro email for assistance.
        </p>
      </div>
    </div>
  );
}
