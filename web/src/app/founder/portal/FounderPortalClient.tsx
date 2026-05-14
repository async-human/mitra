"use client";

import React, { useEffect, useState, useCallback } from "react";
import { UserMenu } from "@/app/dashboard/UserMenu";

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

interface CompanyInfo {
  website_url?: string;
  linkedin_url?: string;
  founded_year?: number;
  employee_range?: string;
  funding_stage?: string;
  total_funding?: string;
  hq_location?: string;
  investors?: string[];
  description?: string;
}

interface PortalJob {
  id: number;
  title: string;
  company: string;
  stage: string | null;
  sector: string | null;
  location: string | null;
  remote_policy: string | null;
  employment: string | null;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  exp_min_yrs: number | null;
  exp_max_yrs: number | null;
  stack: string[];
  summary: string | null;
  responsibilities: string[];
  requirements: string[];
  nice_to_have: string[];
  company_info: CompanyInfo;
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
  const [showForm, setShowForm] = useState<"schedule" | "offer" | null>(null);

  // Interview form state
  const [ivDate, setIvDate] = useState("");
  const [ivTime, setIvTime] = useState("");
  const [ivFormat, setIvFormat] = useState("video");
  const [ivLink, setIvLink] = useState("");

  // Offer form state
  const [ofSalary, setOfSalary] = useState("");
  const [ofEquity, setOfEquity] = useState("");
  const [ofStart, setOfStart] = useState("");
  const [ofNotes, setOfNotes] = useState("");

  const isTerminal = ["declined", "hired"].includes(candidate.status);

  const doAction = useCallback(async (action: string, extraBody?: object) => {
    setActionState("loading");
    try {
      const res = await fetch(`${API_URL}/founder/portal/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, intro_id: candidate.intro_id, action, ...extraBody }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed");
      setToast({ msg: data.message, ok: true });
      setActionState("done");
      setShowForm(null);
      onStatusChange(candidate.intro_id, data.new_status);
    } catch (e: unknown) {
      setActionState("idle");
      setToast({ msg: e instanceof Error ? e.message : "Something went wrong", ok: false });
    }
    setTimeout(() => setToast(null), 4000);
  }, [token, candidate.intro_id, onStatusChange]);

  const submitSchedule = useCallback(() => {
    const scheduledAt = ivDate && ivTime ? `${ivDate}T${ivTime}:00` : undefined;
    doAction("schedule", {
      interview_details: {
        scheduled_at: scheduledAt,
        format: ivFormat,
        link: ivLink || undefined,
      },
    });
  }, [doAction, ivDate, ivTime, ivFormat, ivLink]);

  const submitOffer = useCallback(() => {
    doAction("offer", {
      offer_details: {
        salary_lpa: ofSalary ? Number(ofSalary) : undefined,
        equity_percent: ofEquity ? Number(ofEquity) : undefined,
        start_date: ofStart || undefined,
        notes: ofNotes || undefined,
      },
    });
  }, [doAction, ofSalary, ofEquity, ofStart, ofNotes]);

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

      {/* Inline schedule form */}
      {showForm === "schedule" && (
        <div className="fpc-form">
          <p className="fpc-form-title">Schedule interview</p>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Date</label>
            <input type="date" className="fpc-form-input" value={ivDate} onChange={e => setIvDate(e.target.value)} />
            <label className="fpc-form-label">Time</label>
            <input type="time" className="fpc-form-input" value={ivTime} onChange={e => setIvTime(e.target.value)} />
          </div>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Format</label>
            <select className="fpc-form-input" value={ivFormat} onChange={e => setIvFormat(e.target.value)}>
              <option value="video">Video call</option>
              <option value="phone">Phone call</option>
              <option value="in-person">In-person</option>
            </select>
          </div>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Link / location</label>
            <input type="text" className="fpc-form-input fpc-form-input--wide" placeholder="Meet link or address (optional)" value={ivLink} onChange={e => setIvLink(e.target.value)} />
          </div>
          <div className="fpc-form-actions">
            <button className="fpc-btn fpc-btn--schedule" disabled={actionState === "loading"} onClick={submitSchedule}>
              {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCalendar />}
              Confirm schedule
            </button>
            <button className="fpc-btn fpc-btn--ghost" onClick={() => setShowForm(null)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Inline offer form */}
      {showForm === "offer" && (
        <div className="fpc-form">
          <p className="fpc-form-title">Record offer details</p>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Salary (LPA)</label>
            <input type="number" className="fpc-form-input" placeholder="e.g. 28" value={ofSalary} onChange={e => setOfSalary(e.target.value)} />
            <label className="fpc-form-label">Equity %</label>
            <input type="number" className="fpc-form-input" placeholder="e.g. 0.5" step="0.1" value={ofEquity} onChange={e => setOfEquity(e.target.value)} />
          </div>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Start date</label>
            <input type="date" className="fpc-form-input" value={ofStart} onChange={e => setOfStart(e.target.value)} />
          </div>
          <div className="fpc-form-row">
            <label className="fpc-form-label">Notes for candidate</label>
            <input type="text" className="fpc-form-input fpc-form-input--wide" placeholder="Optional — deadline to respond, next steps, etc." value={ofNotes} onChange={e => setOfNotes(e.target.value)} />
          </div>
          <div className="fpc-form-actions">
            <button className="fpc-btn fpc-btn--offer" disabled={actionState === "loading"} onClick={submitOffer}>
              {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCheck />}
              Record offer
            </button>
            <button className="fpc-btn fpc-btn--ghost" onClick={() => setShowForm(null)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Progressive actions based on current status */}
      {showForm === null && (
        <>
          {candidate.status === "sent" || candidate.status === "ghosted" ? (
            <div className="fpc-actions">
              <button className="fpc-btn fpc-btn--primary" disabled={actionState === "loading"} onClick={() => doAction("interested")}>
                {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCheck />}
                Interested
              </button>
              <button className="fpc-btn fpc-btn--schedule" disabled={actionState === "loading"} onClick={() => setShowForm("schedule")}>
                <IconCalendar />Schedule interview
              </button>
              <button className="fpc-btn fpc-btn--pass" disabled={actionState === "loading"} onClick={() => doAction("not_a_fit")}>
                <IconX />Pass
              </button>
            </div>
          ) : candidate.status === "acknowledged" ? (
            <div className="fpc-actions">
              <button className="fpc-btn fpc-btn--schedule" disabled={actionState === "loading"} onClick={() => setShowForm("schedule")}>
                {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCalendar />}
                Schedule interview
              </button>
              <button className="fpc-btn fpc-btn--pass" disabled={actionState === "loading"} onClick={() => doAction("not_a_fit")}>
                <IconX />Pass
              </button>
            </div>
          ) : candidate.status === "interview" ? (
            <div className="fpc-actions">
              <button className="fpc-btn fpc-btn--offer" disabled={actionState === "loading"} onClick={() => setShowForm("offer")}>
                {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCheck />}
                Offer extended
              </button>
              <button className="fpc-btn fpc-btn--pass" disabled={actionState === "loading"} onClick={() => doAction("not_a_fit")}>
                <IconX />Didn&apos;t proceed
              </button>
            </div>
          ) : candidate.status === "offer" ? (
            <div className="fpc-actions">
              <button className="fpc-btn fpc-btn--hired" disabled={actionState === "loading"} onClick={() => doAction("hired")}>
                {actionState === "loading" ? <span className="fpc-spinner" /> : <IconCheck />}
                They joined! 🎉
              </button>
              <button className="fpc-btn fpc-btn--pass" disabled={actionState === "loading"} onClick={() => doAction("not_a_fit")}>
                <IconX />Offer declined
              </button>
            </div>
          ) : isTerminal ? (
            <div className="fpc-actioned" style={{ borderColor: meta.dot, color: meta.color }}>
              <span className="fpc-actioned-dot" style={{ background: meta.dot }} />
              <span>{meta.label}</span>
              <span className="fpc-actioned-note">· candidate notified</span>
            </div>
          ) : null}
        </>
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

export function FounderPortalClient({
  token,
  sessionUser,
}: {
  token: string;
  sessionUser?: { name?: string | null; email?: string | null; image?: string | null };
}) {
  const [data, setData]             = useState<PortalData | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string>("");
  const [filter, setFilter]         = useState("all");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting]     = useState(false);

  const load = useCallback(() => {
    if (!token) { setError("No portal token provided."); setLoading(false); return; }
    setLoading(true);
    setError("");
    const url = `${API_URL}/founder/portal?token=${encodeURIComponent(token)}`;
    fetch(url)
      .then(async r => {
        if (!r.ok) {
          const detail = await r.json().then((d: { detail?: string }) => d.detail).catch(() => null);
          throw new Error(detail || (r.status === 404 ? "Portal not found or token expired." : `Server error (${r.status})`));
        }
        return r.json();
      })
      .then((d: PortalData) => { setData(d); setLoading(false); })
      .catch((e: Error) => {
        const isNetErr = e.message === "Failed to fetch" || e.message.includes("NetworkError");
        const msg = isNetErr
          ? `Could not reach the server at ${API_URL || "(no API URL set)"}. ${window.location.protocol === "https:" && API_URL.startsWith("http:") ? "⚠️ Mixed content blocked — your API URL must start with https://" : "Check your connection and try again."}`
          : e.message;
        setError(msg);
        setLoading(false);
      });
  }, [token]);

  useEffect(() => { load(); }, [load]);

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

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      const r = await fetch(`${API_URL}/founder/portal/job`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || `Error ${r.status}`);
      }
      window.location.href = "/founder/setup?list=1";
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to delete role.";
      setError(msg);
      setShowDeleteConfirm(false);
      setDeleting(false);
    }
  }, [token]);

  if (loading) return <PortalSkeleton />;
  if (error || !data) return <PortalError message={error || "Something went wrong."} onRetry={load} />;

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
        <div className="fp2-topbar-right">
          <a href="/founder/setup?list=1" className="fp2-topbar-link">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M9 2H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L9 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              <path d="M9 2v3h3M5 8h4M5 10.5h2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            My roles
          </a>
          <a href="/onboarding" className="fp2-topbar-link fp2-topbar-link--accent">
            + Add role
          </a>
          <span className="fp2-topbar-pill">Founder Portal</span>
          {sessionUser?.email ? (
            <UserMenu
              name={sessionUser.name}
              email={sessionUser.email}
              image={sessionUser.image}
            />
          ) : null}
        </div>
      </header>

      <main className="fp2-main">
        <section className="fp2-role-region" aria-labelledby="fp2-role-heading">
          <p id="fp2-role-heading" className="fp2-region-eyebrow">
            Your opening
          </p>
          {/* Job — Dex-style stacked section blocks */}
          <div className="fp2-job-pane">

          {/* Block 1: Header — avatar + title + company + stage + delete */}
          <div className="fp2-job-block fp2-job-block--header">
            <div className="fp2-job-av">
              {job.company.slice(0, 2).toUpperCase()}
            </div>
            <div className="fp2-job-identity">
              <h1 className="fp2-job-title">{job.title}</h1>
              <p className="fp2-job-company">{job.company}</p>
            </div>
            <div className="fp2-job-header-right">
              {job.stage && <span className="fp2-job-stage">{job.stage}</span>}
              <button
                className="fp2-delete-role-btn"
                onClick={() => setShowDeleteConfirm(true)}
                title="Delete this role"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 3.5h10M5.5 3.5V2.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M5 3.5l.5 7M9 3.5l-.5 7M3.5 3.5l.5 8h6l.5-8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Delete role
              </button>
            </div>
          </div>

          {/* Block 2: Meta strip — badges + stack (frameless) */}
          <div className="fp2-job-block fp2-job-block--meta">
            <div className="fp2-job-badges">
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
                  {job.remote_policy.charAt(0).toUpperCase() + job.remote_policy.slice(1)}
                </span>
              )}
              {job.employment && job.employment !== "full_time" && (
                <span className="fp2-job-badge">
                  {job.employment === "contract" ? "Contract" : job.employment === "part_time" ? "Part-time" : job.employment}
                </span>
              )}
              {salaryStr && <span className="fp2-job-badge fp2-job-badge--salary">{salaryStr} / yr</span>}
              {(job.exp_min_yrs || job.exp_max_yrs) && (
                <span className="fp2-job-badge fp2-job-badge--exp">
                  {job.exp_min_yrs && job.exp_max_yrs && job.exp_min_yrs !== job.exp_max_yrs
                    ? `${job.exp_min_yrs}–${job.exp_max_yrs} yrs exp`
                    : `${job.exp_min_yrs ?? job.exp_max_yrs}+ yrs exp`}
                </span>
              )}
              {job.sector && <span className="fp2-job-badge">{job.sector}</span>}
            </div>
            {job.stack.length > 0 && (
              <div className="fp2-job-stack">
                {job.stack.map((t, i) => <span key={i} className="fp2-job-tag">{t}</span>)}
              </div>
            )}
          </div>

          {/* Block 3: About the Role */}
          {job.summary && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">About the Role</p>
              <p className="fp2-job-block-text">{job.summary}</p>
            </div>
          )}

          {/* Block 4: Key Responsibilities */}
          {job.responsibilities.length > 0 && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">Key Responsibilities</p>
              <ul className="fp2-job-block-list">
                {job.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* Block 5: Required Skills & Experience */}
          {job.requirements.length > 0 && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">Required Skills & Experience</p>
              <ul className="fp2-job-block-list">
                {job.requirements.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* Block 6: Preferred Qualifications */}
          {job.nice_to_have.length > 0 && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">Preferred Qualifications</p>
              <ul className="fp2-job-block-list fp2-job-block-list--muted">
                {job.nice_to_have.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* Block 7: About the Company */}
          {(job.company_info.description || job.company_info.founded_year || job.company_info.employee_range || job.company_info.investors?.length) && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">About {job.company}</p>
              {job.company_info.description && (
                <p className="fp2-job-block-text">{job.company_info.description}</p>
              )}
              {(job.company_info.founded_year || job.company_info.employee_range || job.company_info.total_funding || job.company_info.funding_stage || job.company_info.hq_location) && (
                <div className="fp2-company-facts">
                  {job.company_info.founded_year && (
                    <span className="fp2-company-fact">
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        <rect x="1" y="2" width="11" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
                        <path d="M1 5h11M4.5 1v2M8.5 1v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                      </svg>
                      Founded {job.company_info.founded_year}
                    </span>
                  )}
                  {job.company_info.employee_range && (
                    <span className="fp2-company-fact">
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        <circle cx="6.5" cy="4" r="2" stroke="currentColor" strokeWidth="1.3"/>
                        <path d="M2 11c0-2.21 2.015-4 4.5-4S11 8.79 11 11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                      </svg>
                      {job.company_info.employee_range}
                    </span>
                  )}
                  {job.company_info.total_funding && (
                    <span className="fp2-company-fact">
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        <path d="M2 9l3-3 2 2 4-5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      {job.company_info.total_funding} raised
                    </span>
                  )}
                  {job.company_info.funding_stage && (
                    <span className="fp2-company-fact">
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        <rect x="2" y="6" width="2" height="5" rx=".5" fill="currentColor"/>
                        <rect x="5.5" y="4" width="2" height="7" rx=".5" fill="currentColor"/>
                        <rect x="9" y="2" width="2" height="9" rx=".5" fill="currentColor"/>
                      </svg>
                      {job.company_info.funding_stage}
                    </span>
                  )}
                  {job.company_info.hq_location && (
                    <span className="fp2-company-fact">
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        <path d="M6.5 1C4.567 1 3 2.567 3 4.5 3 7.375 6.5 12 6.5 12S10 7.375 10 4.5C10 2.567 8.433 1 6.5 1Z" stroke="currentColor" strokeWidth="1.3"/>
                        <circle cx="6.5" cy="4.5" r="1.2" stroke="currentColor" strokeWidth="1.1"/>
                      </svg>
                      {job.company_info.hq_location}
                    </span>
                  )}
                </div>
              )}
              {job.company_info.investors && job.company_info.investors.length > 0 && (
                <div>
                  <p className="fp2-company-investors-label">Investors</p>
                  <div className="fp2-company-investors">
                    {job.company_info.investors.map((inv, i) => (
                      <span key={i} className="fp2-company-investor-tag">{inv}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Block 8: Company Links */}
          {(job.company_info.website_url || job.company_info.linkedin_url) && (
            <div className="fp2-job-block">
              <p className="fp2-job-block-title">Company Links</p>
              <div className="fp2-company-links">
                {job.company_info.website_url && (
                  <a href={job.company_info.website_url} target="_blank" rel="noopener noreferrer" className="fp2-company-link-btn">
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                      <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
                      <path d="M6.5 1C5 3 4 4.7 4 6.5s1 3.5 2.5 5.5M6.5 1C8 3 9 4.7 9 6.5S8 10 6.5 12M1 6.5h11" stroke="currentColor" strokeWidth="1.1"/>
                    </svg>
                    Website
                  </a>
                )}
                {job.company_info.linkedin_url && (
                  <a href={job.company_info.linkedin_url} target="_blank" rel="noopener noreferrer" className="fp2-company-link-btn">
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                      <rect x="1" y="1" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.3"/>
                      <path d="M4 5.5v4M4 4v-.5M6.5 9.5V7c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                    </svg>
                    LinkedIn
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Pipeline for this role */}
        <StatsBar stats={stats} />
        </section>

        {/* Delete confirmation modal */}
        {showDeleteConfirm && (
          <div className="fp2-modal-overlay" onClick={() => !deleting && setShowDeleteConfirm(false)}>
            <div className="fp2-modal" onClick={e => e.stopPropagation()}>
              <div className="fp2-modal-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="#E85B4A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h3 className="fp2-modal-title">Delete this role?</h3>
              <p className="fp2-modal-body">
                <strong>{job.title}</strong> at <strong>{job.company}</strong> will be removed from your portal and Mitra will stop sending new introductions. All existing candidate history will be preserved.
              </p>
              <div className="fp2-modal-actions">
                <button
                  className="fp2-modal-btn fp2-modal-btn--danger"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? "Deleting…" : "Yes, delete role"}
                </button>
                <button
                  className="fp2-modal-btn fp2-modal-btn--ghost"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        <section
          className="fp2-candidates-region"
          aria-labelledby="fp2-intros-heading"
        >
          <h2 id="fp2-intros-heading" className="fp2-section-label fp2-section-label--candidates">
            <span>Introductions</span>
            <span className="fp2-section-count">{candidates.length}</span>
          </h2>

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
        </section>
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

function PortalError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const isNetworkErr = message.toLowerCase().includes("reach") || message.toLowerCase().includes("fetch");
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
        <h2 className="fp2-error-title">
          {isNetworkErr ? "Connection error" : "Portal unavailable"}
        </h2>
        <p className="fp2-error-desc">{message}</p>
        {!isNetworkErr && (
          <p className="fp2-error-hint">
            If you received this link via email, it may have expired.<br />
            Reply to the original intro email for assistance.
          </p>
        )}
        {onRetry && (
          <button className="fp2-error-retry" onClick={onRetry}>
            Try again
          </button>
        )}
        <a href="/founder/setup" className="fp2-error-back">
          ← Back to portal home
        </a>
      </div>
    </div>
  );
}
