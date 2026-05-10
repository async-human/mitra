"use client";

import { useEffect, useState, useCallback } from "react";

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

// ── Status config ──────────────────────────────────────────────────────────────

const STATUS: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  sent:         { label: "Intro sent",       color: "#059669", bg: "#ECFDF5", dot: "#34D399" },
  acknowledged: { label: "Interested",       color: "#7C3AED", bg: "#F5F3FF", dot: "#A78BFA" },
  interview:    { label: "Interview set",    color: "#D97706", bg: "#FFFBEB", dot: "#FCD34D" },
  offer:        { label: "Offer extended",   color: "#2563EB", bg: "#EFF6FF", dot: "#93C5FD" },
  hired:        { label: "Hired 🎉",         color: "#059669", bg: "#D1FAE5", dot: "#6EE7B7" },
  declined:     { label: "Not a fit",        color: "#6B7280", bg: "#F3F4F6", dot: "#D1D5DB" },
  ghosted:      { label: "Awaiting reply",   color: "#9CA3AF", bg: "#F9FAFB", dot: "#E5E7EB" },
};
function statusMeta(s: string) {
  return STATUS[s] ?? { label: s, color: "#6B7280", bg: "#F3F4F6", dot: "#D1D5DB" };
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function initials(name: string | null, role: string | null): string {
  const n = (name || role || "??").trim();
  const parts = n.split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : n.slice(0, 2).toUpperCase();
}

function salaryLabel(min: number | null, max: number | null) {
  if (!min && !max) return null;
  if (min && max && min !== max) return `₹${min}–${max}L`;
  return `₹${min || max}L`;
}

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

const AVATAR_COLORS = [
  ["#DBEAFE", "#3B82F6"], ["#FEF3C7", "#D97706"], ["#D1FAE5", "#059669"],
  ["#EDE9FE", "#7C3AED"], ["#FFE4E6", "#E11D48"], ["#E0F2FE", "#0284C7"],
];
function avatarColor(idx: number) { return AVATAR_COLORS[idx % AVATAR_COLORS.length]; }

// ── Stat chip ─────────────────────────────────────────────────────────────────

function StatChip({ value, label, accent }: { value: number; label: string; accent?: string }) {
  return (
    <div className="fp-stat-chip">
      <span className="fp-stat-num" style={accent ? { color: accent } : undefined}>{value}</span>
      <span className="fp-stat-label">{label}</span>
    </div>
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
  const [bg, fg] = avatarColor(idx);
  const [actionState, setActionState] = useState<"idle" | "loading" | "done">("idle");
  const [toast, setToast] = useState<string>("");
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
      setToast(data.message);
      setActionState("done");
      onStatusChange(candidate.intro_id, data.new_status);
    } catch (e: unknown) {
      setActionState("idle");
      setToast(e instanceof Error ? e.message : "Something went wrong");
    }
    setTimeout(() => setToast(""), 4000);
  }, [token, candidate.intro_id, onStatusChange]);

  return (
    <div className={`fp-card fp-card--${candidate.status}`} style={{ animationDelay: `${idx * 0.06}s` }}>
      {/* Header row */}
      <div className="fp-card-header">
        <div className="fp-avatar" style={{ background: bg, color: fg }}>
          {initials(s.name, s.current_role)}
        </div>
        <div className="fp-card-identity">
          <h3 className="fp-candidate-name">{s.name || "Anonymous Candidate"}</h3>
          <p className="fp-candidate-role">
            {s.current_role || "Engineer"}
            {s.current_company ? ` · ${s.current_company}` : ""}
          </p>
        </div>
        <span className="fp-status-badge" style={{ color: meta.color, background: meta.bg }}>
          <span className="fp-status-dot" style={{ background: meta.dot }} />
          {meta.label}
        </span>
      </div>

      {/* Signals grid */}
      <div className="fp-signals">
        {s.years_exp != null && (
          <div className="fp-signal-chip">
            <span className="fp-signal-icon">⏱</span>
            <span>{s.years_exp}y exp</span>
          </div>
        )}
        {s.salary_target_lpa != null && (
          <div className="fp-signal-chip">
            <span className="fp-signal-icon">₹</span>
            <span>{s.salary_target_lpa}L target</span>
          </div>
        )}
        {s.notice_period_days != null && (
          <div className="fp-signal-chip">
            <span className="fp-signal-icon">📅</span>
            <span>{s.notice_period_days}d notice</span>
          </div>
        )}
        {candidate.sent_at && (
          <div className="fp-signal-chip fp-signal-chip--muted">
            <span className="fp-signal-icon">✉</span>
            <span>Introduced {formatDate(candidate.sent_at)}</span>
          </div>
        )}
      </div>

      {/* Stack tags */}
      {s.stack.length > 0 && (
        <div className="fp-stack">
          {s.stack.slice(0, 6).map((t, i) => (
            <span key={i} className="fp-stack-tag">{t}</span>
          ))}
        </div>
      )}

      {/* Why Mitra made this intro */}
      {candidate.why_note && (
        <div className="fp-why-box">
          <span className="fp-why-label">✦ Why Mitra introduced them</span>
          <p className="fp-why-text">{candidate.why_note}</p>
        </div>
      )}

      {/* Motivation */}
      {s.motivation && (
        <p className="fp-motivation">
          <span className="fp-motivation-label">Looking for:</span> {s.motivation}
        </p>
      )}

      {/* Notable projects */}
      {s.notable_projects && (
        <p className="fp-motivation">
          <span className="fp-motivation-label">Built:</span> {s.notable_projects}
        </p>
      )}

      {/* Toast */}
      {toast && <div className="fp-toast">{toast}</div>}

      {/* Actions */}
      {!isActioned && (
        <div className="fp-actions">
          <button
            className="fp-btn fp-btn--interested"
            disabled={actionState === "loading"}
            onClick={() => doAction("interested")}
          >
            {actionState === "loading" ? <span className="fp-btn-spinner" /> : "✓"}
            Interested
          </button>
          <button
            className="fp-btn fp-btn--schedule"
            disabled={actionState === "loading"}
            onClick={() => doAction("schedule")}
          >
            📅 Schedule interview
          </button>
          <button
            className="fp-btn fp-btn--decline"
            disabled={actionState === "loading"}
            onClick={() => doAction("not_a_fit")}
          >
            Not a fit
          </button>
        </div>
      )}

      {/* Already-actioned state */}
      {isActioned && candidate.status !== "declined" && (
        <div className="fp-actioned-strip" style={{ background: meta.bg, color: meta.color }}>
          <span className="fp-status-dot" style={{ background: meta.dot }} />
          {meta.label} — candidate has been notified
        </div>
      )}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="fp-empty">
      <div className="fp-empty-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
          <circle cx="24" cy="24" r="22" stroke="currentColor" strokeWidth="1.5" />
          <path d="M16 24h16M24 16v16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <h3 className="fp-empty-title">No candidates yet</h3>
      <p className="fp-empty-sub">Mitra is actively searching for the best fit. You'll get an email as soon as we have a strong introduction to make.</p>
    </div>
  );
}

// ── Pipeline filter bar ───────────────────────────────────────────────────────

const FILTERS = [
  { key: "all",         label: "All" },
  { key: "sent",        label: "New" },
  { key: "acknowledged",label: "Interested" },
  { key: "interview",   label: "Interview" },
  { key: "offer",       label: "Offer" },
  { key: "declined",    label: "Declined" },
];

// ── Main portal component ──────────────────────────────────────────────────────

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
      return {
        ...prev,
        candidates: prev.candidates.map(c =>
          c.intro_id === introId ? { ...c, status: newStatus } : c
        ),
        stats: {
          ...prev.stats,
          interested: prev.candidates.filter(c =>
            (c.intro_id === introId ? newStatus : c.status) === "acknowledged"
          ).length,
          interview: prev.candidates.filter(c =>
            (c.intro_id === introId ? newStatus : c.status) === "interview"
          ).length,
        },
      };
    });
  }, []);

  if (loading) return <PortalSkeleton />;
  if (error || !data) return <PortalError message={error || "Something went wrong."} />;

  const { job, candidates, stats } = data;

  const filtered = filter === "all" ? candidates : candidates.filter(c => c.status === filter);
  const activeCounts: Record<string, number> = {};
  for (const c of candidates) {
    activeCounts[c.status] = (activeCounts[c.status] ?? 0) + 1;
  }

  return (
    <div className="fp-root">
      {/* Top bar */}
      <header className="fp-topbar">
        <div className="fp-topbar-inner">
          <span className="fp-logo">Mitra<span className="fp-logo-dot">.</span></span>
          <span className="fp-topbar-tag">Founder Portal</span>
        </div>
      </header>

      <main className="fp-main">
        {/* Job hero */}
        <section className="fp-hero">
          <div className="fp-hero-av">{job.company.slice(0, 2).toUpperCase()}</div>
          <div className="fp-hero-info">
            <h1 className="fp-hero-title">{job.title}</h1>
            <p className="fp-hero-company">{job.company}</p>
            <div className="fp-hero-badges">
              {job.stage   && <span className="fp-badge">{job.stage}</span>}
              {job.sector  && <span className="fp-badge">{job.sector}</span>}
              {job.location && <span className="fp-badge">📍 {job.location}</span>}
              {job.remote_policy === "remote" && <span className="fp-badge">🌐 Remote</span>}
              {job.remote_policy === "hybrid" && <span className="fp-badge">🏢 Hybrid</span>}
              {salaryLabel(job.salary_min_lpa, job.salary_max_lpa) && (
                <span className="fp-badge">
                  {salaryLabel(job.salary_min_lpa, job.salary_max_lpa)} / year
                </span>
              )}
            </div>
            {job.stack.length > 0 && (
              <div className="fp-hero-stack">
                {job.stack.map((t, i) => <span key={i} className="fp-stack-tag fp-stack-tag--hero">{t}</span>)}
              </div>
            )}
          </div>
        </section>

        {/* Stats bar */}
        <section className="fp-stats-bar">
          <StatChip value={stats.total}      label="introduced"  />
          <div className="fp-stats-divider" />
          <StatChip value={stats.interested} label="interested"  accent="#7C3AED" />
          <StatChip value={stats.interview}  label="interviewing" accent="#D97706" />
          <StatChip value={stats.offer}      label="offer"       accent="#2563EB" />
          <StatChip value={stats.hired}      label="hired"       accent="#059669" />
        </section>

        {/* Filter tabs */}
        {candidates.length > 0 && (
          <div className="fp-filter-bar">
            {FILTERS.map(f => {
              const count = f.key === "all" ? candidates.length : (activeCounts[f.key] ?? 0);
              if (f.key !== "all" && count === 0) return null;
              return (
                <button
                  key={f.key}
                  className={`fp-filter-tab${filter === f.key ? " fp-filter-tab--active" : ""}`}
                  onClick={() => setFilter(f.key)}
                >
                  {f.label}
                  {count > 0 && <span className="fp-filter-count">{count}</span>}
                </button>
              );
            })}
          </div>
        )}

        {/* Candidate list */}
        <section className="fp-candidates">
          {filtered.length === 0 ? (
            <EmptyState />
          ) : (
            filtered.map((c, i) => (
              <CandidateCard
                key={c.intro_id}
                candidate={c}
                idx={i}
                token={token}
                onStatusChange={handleStatusChange}
              />
            ))
          )}
        </section>

        {/* Footer note */}
        <p className="fp-footer-note">
          All introductions are curated by Mitra — AI talent agent for funded startups.
          Questions? Reply to the intro email.
        </p>
      </main>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function PortalSkeleton() {
  return (
    <div className="fp-root">
      <header className="fp-topbar">
        <div className="fp-topbar-inner">
          <span className="fp-logo">Mitra<span className="fp-logo-dot">.</span></span>
          <span className="fp-topbar-tag">Founder Portal</span>
        </div>
      </header>
      <main className="fp-main">
        <section className="fp-hero fp-hero--sk">
          <div className="fp-hero-av fp-sk" />
          <div className="fp-hero-info" style={{ flex: 1 }}>
            <div className="fp-sk" style={{ height: 28, width: "55%", borderRadius: 6, marginBottom: 10 }} />
            <div className="fp-sk" style={{ height: 16, width: "35%", borderRadius: 4, marginBottom: 14 }} />
            <div style={{ display: "flex", gap: 8 }}>
              {[60, 80, 70].map((w, i) => (
                <div key={i} className="fp-sk" style={{ height: 26, width: w, borderRadius: 20 }} />
              ))}
            </div>
          </div>
        </section>
        <div className="fp-stats-bar">
          {[1,2,3,4].map(i => (
            <div key={i} className="fp-stat-chip">
              <div className="fp-sk" style={{ height: 28, width: 28, borderRadius: 4, marginBottom: 6 }} />
              <div className="fp-sk" style={{ height: 12, width: 50, borderRadius: 4 }} />
            </div>
          ))}
        </div>
        <section className="fp-candidates">
          {[0,1,2].map(i => (
            <div key={i} className="fp-card" style={{ animationDelay: `${i * 0.08}s` }}>
              <div className="fp-card-header">
                <div className="fp-sk" style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0 }} />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                  <div className="fp-sk" style={{ height: 16, width: "50%", borderRadius: 4 }} />
                  <div className="fp-sk" style={{ height: 13, width: "35%", borderRadius: 4 }} />
                </div>
                <div className="fp-sk" style={{ height: 24, width: 80, borderRadius: 20 }} />
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                {[60, 80, 70, 90].map((w, j) => (
                  <div key={j} className="fp-sk" style={{ height: 28, width: w, borderRadius: 20 }} />
                ))}
              </div>
              <div className="fp-sk" style={{ height: 68, borderRadius: 10, marginTop: 14 }} />
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}

// ── Error ──────────────────────────────────────────────────────────────────────

function PortalError({ message }: { message: string }) {
  return (
    <div className="fp-root fp-root--center">
      <div className="fp-error-card">
        <div className="fp-error-icon">⚠</div>
        <h2 className="fp-error-title">Portal unavailable</h2>
        <p className="fp-error-desc">{message}</p>
        <p className="fp-error-desc" style={{ marginTop: 8, fontSize: 13 }}>
          If you received this link via email, it may have expired.<br />
          Reply to the original intro email for assistance.
        </p>
      </div>
    </div>
  );
}
