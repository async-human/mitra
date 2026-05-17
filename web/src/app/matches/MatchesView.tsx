"use client";

import { useEffect, useState, useCallback, Fragment } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { deriveMatchCardsFromIntros } from "@/app/dashboard/deriveMatchCards";
import type { CandidateIntro } from "@/app/dashboard/introTypes";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface BasicCard { id: string; title: string; description: string; why?: string; recommended_at?: string; }
interface FullJob {
  id: number; external_id: string | null;
  title: string; company: string;
  stage: string | null; sector: string | null;
  location: string | null; remote_policy: string | null;
  employment: string | null;
  salary_min_lpa: number | null; salary_max_lpa: number | null;
  stack: string[]; summary: string | null;
  signals: Record<string, string>;
  full_jd: string | null;
}
interface MergedJob extends FullJob {
  external_id: string;
  fit: string; fit_pct: number; why: string;
  recommended_at?: string;
}

// ── Date grouping ─────────────────────────────────────────────────────────────

type DateGroup = "Today" | "Yesterday" | "This week" | "Earlier";

function dateGroupLabel(iso: string | undefined): DateGroup {
  if (!iso) return "Earlier";
  const d    = new Date(iso);
  const now  = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86_400_000);
  if (d.toDateString() === now.toDateString()) return "Today";
  if (diff === 1)  return "Yesterday";
  if (diff <= 6)   return "This week";
  return "Earlier";
}

const GROUP_ORDER: DateGroup[] = ["Today", "Yesterday", "This week", "Earlier"];

function groupAndSort(jobs: MergedJob[]): { label: DateGroup; jobs: MergedJob[] }[] {
  // Sort each group by fit_pct descending (best fit first)
  const buckets: Record<DateGroup, MergedJob[]> = {
    "Today": [], "Yesterday": [], "This week": [], "Earlier": [],
  };
  for (const job of jobs) {
    buckets[dateGroupLabel(job.recommended_at)].push(job);
  }
  for (const label of GROUP_ORDER) {
    buckets[label].sort((a, b) => b.fit_pct - a.fit_pct);
  }
  return GROUP_ORDER
    .filter(label => buckets[label].length > 0)
    .map(label => ({ label, jobs: buckets[label] }));
}

type IntroStatus = "idle" | "loading" | "sent" | "already_sent" | "error" | "needs_info";

function buildStrengthenIntroHref(job: MergedJob, missing: string[]): string {
  const q = new URLSearchParams();
  q.set("intent", "strengthen_intro");
  q.set("job_id", job.external_id ?? String(job.id));
  q.set("company", job.company);
  q.set("role", job.title);
  if (missing.length > 0) {
    q.set("missing", missing.join("|"));
  }
  return `/chat?${q.toString()}`;
}

/** Parse checklist from gate message when API omits missing_signals (old servers / proxies). */
function parseMissingFromGateMessage(message: string): string[] {
  const startM = message.match(/details first:\s*/i);
  if (!startM || startM.index === undefined) return [];
  const from = startM.index + startM[0].length;
  const tail = message.slice(from);
  const endM = tail.match(/\.\s*(?:A complete intro|Can you share)/i);
  const end = endM && endM.index !== undefined ? from + endM.index : message.length;
  const chunk = message.slice(from, end).trim();
  if (!chunk) return [];
  const raw = chunk.split(", your ");
  return raw.map((p, i) => (i === 0 ? p.trim() : `your ${p.trim()}`)).filter(Boolean);
}

function extractIntroApiPayload(data: unknown): {
  ok: boolean;
  message: string;
  needsMoreInfo: boolean;
  missingSignals: string[];
  alreadySent: boolean;
} {
  if (!data || typeof data !== "object") {
    return {
      ok: false,
      message: "",
      needsMoreInfo: false,
      missingSignals: [],
      alreadySent: false,
    };
  }
  const o = data as Record<string, unknown>;
  const msg = typeof o.message === "string" ? o.message : "";
  const ok = o.ok === true;
  const rawNeeds =
    o.needs_more_info === true ||
    o.needs_more_info === "true" ||
    o.needsMoreInfo === true ||
    o.needsMoreInfo === "true";
  let missing: string[] = [];
  if (Array.isArray(o.missing_signals)) {
    missing = o.missing_signals.filter((x): x is string => typeof x === "string");
  } else if (Array.isArray(o.missingSignals)) {
    missing = o.missingSignals.filter((x): x is string => typeof x === "string");
  }
  const already =
    o.already_sent === true ||
    o.alreadySent === true ||
    (!ok && /already sent/i.test(msg));
  return { ok, message: msg, needsMoreInfo: rawNeeds, missingSignals: missing, alreadySent: already };
}

function isIntroGateBlocked(payload: ReturnType<typeof extractIntroApiPayload>): boolean {
  if (payload.needsMoreInfo) return true;
  if (payload.ok || payload.alreadySent) return false;
  const m = payload.message;
  return (
    /few more details first:/i.test(m) ||
    /need a few more details/i.test(m) ||
    /make it strong enough that/i.test(m)
  );
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
    const extra = parts.filter((_, j) => j !== 0 && j !== fitIdx);
    return {
      id: i + 1,
      external_id: b.id,
      title: b.title, company,
      stage: null, sector: null, location: null, remote_policy: null,
      employment: null, salary_min_lpa: null, salary_max_lpa: null,
      stack: extra, summary: null, signals: {}, full_jd: null,
      fit, fit_pct,
      why: b.why ?? "",
      recommended_at: b.recommended_at,
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

function stageBadgeVariant(stage: string): string {
  const s = stage.toLowerCase();
  if (s.includes("seed")) return "seed";
  if (/series\s*[ab]/i.test(s)) return "early";
  if (/series\s*[c-z]/i.test(s) || s.includes("growth") || s.includes("late")) return "late";
  return "default";
}

function StageBadge({ stage }: { stage: string }) {
  return (
    <span className={`match-stage-badge match-stage-badge--${stageBadgeVariant(stage)}`}>
      {stage.toUpperCase()}
    </span>
  );
}

function FullJDSection({ jd }: { jd: string }) {
  return (
    <details className="match-jd">
      <summary className="match-jd-toggle">
        <span>Full job description</span>
        <span className="match-jd-chevron" aria-hidden>›</span>
      </summary>
      <div className="match-jd-content">
        <p className="match-jd-text">{jd}</p>
      </div>
    </details>
  );
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

const RANK_LABELS = ["Top pick", "Strong match", "Worth exploring"];

function SkeletonCard({ delay = 0 }: { delay?: number }) {
  return (
    <div className="match-card match-skeleton-card" style={{ animationDelay: `${delay}s` }}>
      {/* Rank strip */}
      <div className="match-rank-strip">
        <span className="sk-block" style={{ width: 24, height: 12, borderRadius: 4 }} />
        <span className="sk-block" style={{ width: 80, height: 12, borderRadius: 4 }} />
      </div>

      <div className="match-card-top">
        {/* Header */}
        <div className="match-card-header">
          <div className="sk-avatar" />
          <div className="match-card-meta" style={{ gap: 6, display: "flex", flexDirection: "column" }}>
            <span className="sk-block" style={{ width: "60%", height: 14 }} />
            <span className="sk-block" style={{ width: "40%", height: 11 }} />
          </div>
          <div className="sk-fit-badge" />
        </div>

        {/* Stars */}
        <div className="match-stars-row">
          <span className="sk-block" style={{ width: 84, height: 12 }} />
        </div>

        {/* Pills */}
        <div className="match-pills">
          {[52, 64, 44].map((w, i) => (
            <span key={i} className="sk-block" style={{ width: w, height: 22, borderRadius: 100 }} />
          ))}
        </div>
      </div>

      <div className="match-card-why-slot">
        <div className="sk-why-box">
          <span className="sk-block" style={{ width: "50%", height: 11, marginBottom: 8 }} />
          <span className="sk-block" style={{ width: "100%", height: 11, marginBottom: 5 }} />
          <span className="sk-block" style={{ width: "85%", height: 11 }} />
        </div>
      </div>

      {/* Buttons */}
      <div className="match-actions">
        <span className="sk-block" style={{ flex: 1, height: 38, borderRadius: 10 }} />
        <span className="sk-block" style={{ flex: 1, height: 38, borderRadius: 10 }} />
      </div>
    </div>
  );
}

function WhyFits({ job }: { job: MergedJob }) {
  const whyText = job.why || job.summary;
  return (
    <div className="match-why">
      <div className="match-why-header">
        <span className="match-why-icon">✦</span>
        <span className="match-why-label">Why Mitra thinks this fits you</span>
      </div>
      {whyText ? (
        <p className="match-why-text">{whyText}</p>
      ) : (
        <p className="match-why-text match-why-text--placeholder">
          Personalized fit notes show up here when this role came from your Mitra shortlist in chat.
        </p>
      )}
    </div>
  );
}

function CheckCircleIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill="#D1FAE5" stroke="#34D399" strokeWidth="1.5" />
      <path d="M10 16.5l4.5 4.5 7.5-9" stroke="#059669" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <rect x="1" y="3" width="11" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M1 4.5l5.5 3.5 5.5-3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function weakIntroDisplayMissing(stored: string[]): string[] {
  return stored.length > 0 ? stored : ["A few profile details still needed for this intro"];
}

function WeakIntroModal({
  job,
  missing,
  userEmail,
  introStatus,
  onClose,
  onRetry,
}: {
  job: MergedJob;
  missing: string[];
  userEmail?: string;
  introStatus: IntroStatus;
  onClose: () => void;
  onRetry: (job: MergedJob) => void;
}) {
  const [mounted, setMounted] = useState(false);
  const displayMissing = weakIntroDisplayMissing(missing);
  const showBadge = missing.length > 1;
  const chatHref = buildStrengthenIntroHref(job, missing);
  const isLoading = introStatus === "loading";

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [mounted, onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="match-modal-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="match-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="weak-intro-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="match-modal-close" aria-label="Close dialog" onClick={onClose}>
          ×
        </button>
        <div className="match-modal-body">
          <div className="match-weak-modal" role="status">
            <div className="match-weak-modal__hero">
              <div className="match-weak-modal__icon" aria-hidden>
                <span className="match-weak-modal__icon-inner">✦</span>
              </div>
              <div className="match-weak-modal__intro">
                <p className="match-weak-modal__eyebrow">One quick step</p>
                <h2 id="weak-intro-modal-title" className="match-weak-modal__title">
                  Almost there
                </h2>
                <p className="match-weak-modal__lead">
                  Your match is saved. Spend a minute in chat to fill in what&apos;s missing, then retry — we&apos;ll send a strong intro to{" "}
                  <span className="match-weak-modal__company">{job.company}</span>.
                </p>
              </div>
            </div>

            <details className="match-weak-modal__details">
              <summary className="match-weak-modal__summary">
                <span className="match-weak-modal__summary-label">What&apos;s missing</span>
                {showBadge ? (
                  <span className="match-weak-modal__pill">{displayMissing.length}</span>
                ) : null}
                <span className="match-weak-modal__chev" aria-hidden />
              </summary>
              <ul className="match-weak-modal__list">
                {displayMissing.map((item, i) => (
                  <li key={`${item}-${i}`}>{item}</li>
                ))}
              </ul>
            </details>

            <div className="match-weak-modal__actions">
              <Link
                href={chatHref}
                className="match-weak-modal__btn match-weak-modal__btn--primary"
                onClick={onClose}
              >
                Continue with Mitra
              </Link>
              <button
                type="button"
                className={`match-weak-modal__btn match-weak-modal__btn--secondary${isLoading ? " match-weak-modal__btn--busy" : ""}`}
                disabled={!userEmail || isLoading}
                onClick={() => onRetry(job)}
              >
                {isLoading ? <span className="match-btn-spinner" aria-label="Loading" /> : "Retry intro"}
              </button>
            </div>

            <div className="match-weak-modal__footer">
              <Link
                href={`/chat?about=${encodeURIComponent(job.title)}`}
                className="match-weak-modal__tertiary"
                onClick={onClose}
              >
                Ask about something else
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function IntroSuccessFooter({ company, already }: { company: string; already?: boolean }) {
  return (
    <div className={`match-intro-footer${already ? " match-intro-footer--already" : ""}`}>
      <div className="match-intro-footer-icon">
        {already ? (
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <circle cx="16" cy="16" r="15" fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1.5" />
            <path d="M10 16.5l4.5 4.5 7.5-9" stroke="#9CA3AF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <CheckCircleIcon />
        )}
      </div>
      <div className="match-intro-footer-body">
        <p className="match-intro-footer-title">
          {already ? `Intro already submitted to ${company}` : `Intro submitted to ${company}`}
        </p>
        <p className="match-intro-footer-sub">
          {already
            ? "Chat with Mitra to share more for a stronger follow-up"
            : (
              <>
                <MailIcon />
                {" "}We sent a copy to your inbox · expect a reply in 24–48 hrs
              </>
            )
          }
        </p>
      </div>
    </div>
  );
}

function JobCard({
  job, idx, userEmail, introStatus, introError, introMissing: _introMissing, onRequestIntro, onShowWeakIntro, onDismiss,
}: {
  job: MergedJob;
  idx: number;
  userEmail?: string;
  introStatus: IntroStatus;
  introError: string;
  introMissing: string[];
  onRequestIntro: (job: MergedJob) => void;
  onShowWeakIntro?: () => void;
  onDismiss: (id: number) => void;
}) {
  const salary = salaryLabel(job.salary_min_lpa, job.salary_max_lpa);
  const remote = remoteLabel(job.remote_policy);
  const empType = employmentLabel(job.employment);
  const pills = [empType, remote, job.location, job.sector, salary].filter(Boolean) as string[];
  const rankLabel = RANK_LABELS[idx] ?? null;
  const isSent = introStatus === "sent" || introStatus === "already_sent";
  const needsProfile = introStatus === "needs_info";

  return (
    <div
      className={`match-card${isSent ? " match-card--sent" : ""}${introStatus === "already_sent" ? " match-card--already" : ""}`}
      style={{ animationDelay: `${idx * 0.09}s` }}
    >
      {/* Rank strip */}
      {rankLabel && (
        <div className="match-rank-strip">
          <span className="match-rank-num">#{idx + 1}</span>
          <span className="match-rank-label">{rankLabel}</span>
        </div>
      )}

      <div className="match-card-top">
        {/* Card header */}
        <div className="match-card-header">
          <div className="match-company-av">
            {job.company.slice(0, 2).toUpperCase()}
          </div>
          <div className="match-card-meta">
            <h2 className="match-role">{job.title}</h2>
            <div className="match-company-row">
              <p className="match-company">{job.company}</p>
              {job.stage && <StageBadge stage={job.stage} />}
            </div>
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

        {/* Pills */}
        {pills.length > 0 && (
          <div className="match-pills">
            {pills.map((p, i) => <span key={i} className="match-pill">{p}</span>)}
          </div>
        )}

        {/* Stack tags */}
        {job.stack.length > 0 && (
          <div className="match-stack">
            {job.stack.map((s, i) => <span key={i} className="match-stack-tag">{s}</span>)}
          </div>
        )}
      </div>

      <div className="match-card-why-slot">
        <WhyFits job={job} />
      </div>

      {job.full_jd && <FullJDSection jd={job.full_jd} />}

      {/* Actions — weak intro uses same row + modal */}
      {!isSent ? (
        <div className="match-actions">
          <button
            type="button"
            className="match-btn match-btn--dismiss"
            onClick={() => onDismiss(job.id)}
            title="Remove this role from your list"
          >
            Not for me
          </button>
          <Link href={`/chat?about=${encodeURIComponent(job.title)}`} className="match-btn match-btn--ghost">
            Ask Mitra →
          </Link>
          <div className="match-intro-col">
            <button
              className={`match-btn match-btn--primary${introStatus === "loading" ? " match-btn--loading" : ""}`}
              disabled={introStatus === "loading" || !userEmail}
              onClick={() => onRequestIntro(job)}
            >
              {introStatus === "loading" ? (
                <span className="match-btn-spinner" />
              ) : introStatus === "error" ? (
                "Try again"
              ) : needsProfile ? (
                "Retry intro"
              ) : (
                "Request intro"
              )}
            </button>
            {needsProfile && onShowWeakIntro && (
              <button type="button" className="match-intro-weak-hint" onClick={onShowWeakIntro}>
                What&apos;s missing?
              </button>
            )}
            {introStatus === "error" && introError && (
              <p className="match-intro-error">{introError}</p>
            )}
          </div>
        </div>
      ) : null}

      {/* Success footer — replaces the actions row entirely */}
      {isSent && (
        <IntroSuccessFooter
          company={job.company}
          already={introStatus === "already_sent"}
        />
      )}
    </div>
  );
}

function matchesKey(email?: string) {
  return email ? `mitra-matches-${email}` : "mitra-matches";
}

function dismissedKey(email?: string) {
  return email ? `mitra-dismissed-${email}` : "mitra-dismissed";
}

export function MatchesView({ userName, userEmail, urlIds }: { userName?: string; userEmail?: string; urlIds?: string }) {
  const [jobs, setJobs] = useState<MergedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [introStatuses, setIntroStatuses] = useState<Record<number, IntroStatus>>({});
  const [introErrors, setIntroErrors] = useState<Record<number, string>>({});
  const [introMissingByJob, setIntroMissingByJob] = useState<Record<number, string[]>>({});
  const [weakIntroModal, setWeakIntroModal] = useState<null | { job: MergedJob; missing: string[] }>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<number>>(() => {
    try {
      const raw = localStorage.getItem(dismissedKey(userEmail));
      return raw ? new Set<number>(JSON.parse(raw)) : new Set<number>();
    } catch { return new Set<number>(); }
  });
  const firstName = userName?.split(" ")[0];

  const handleDismiss = useCallback((id: number) => {
    setDismissedIds(prev => {
      const next = new Set(prev);
      next.add(id);
      try {
        localStorage.setItem(dismissedKey(userEmail), JSON.stringify([...next]));
      } catch { /* ignore */ }
      return next;
    });
  }, [userEmail]);

  useEffect(() => {
    async function load() {
      const raw = localStorage.getItem(matchesKey(userEmail))
        ?? localStorage.getItem("mitra-matches");
      let basic: BasicCard[] | null = null;
      if (raw) {
        try { basic = JSON.parse(raw); } catch { basic = null; }
      }

      if ((!basic || basic.length === 0) && userEmail) {
        try {
          const r = await fetch(
            `${API_URL}/candidate/intros?session_id=${encodeURIComponent(userEmail)}`,
          );
          if (r.ok) {
            const data: unknown = await r.json();
            if (Array.isArray(data) && data.length > 0) {
              const derived = deriveMatchCardsFromIntros(data as CandidateIntro[]);
              basic = derived;
              try {
                localStorage.setItem(matchesKey(userEmail), JSON.stringify(derived));
              } catch { /* ignore */ }
            }
          }
        } catch { /* ignore */ }
      }

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
          const merged = full.map(f => {
            // Match BasicCard by numeric id OR by external_id (for UUID-style row_ids)
            const b = basic?.find(c => {
              const stripped = c.id.replace(/^job_/, "");
              return Number(stripped) === f.id
                || (f.external_id && stripped === f.external_id);
            });
            const { fit, fit_pct } = parseFit(b?.description ?? "");
            return {
              ...f,
              external_id: f.external_id ?? String(f.id),
              fit, fit_pct,
              why: b?.why ?? "",
              recommended_at: b?.recommended_at,
            };
          });
          setJobs(merged);
        } else if (basic && basic.length > 0) {
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
  }, [urlIds, userEmail]);

  const handleRequestIntro = useCallback(async (job: MergedJob) => {
    if (!userEmail) return;

    setIntroStatuses(prev => ({ ...prev, [job.id]: "loading" }));
    setIntroErrors(prev => ({ ...prev, [job.id]: "" }));

    try {
      const res = await fetch(`${API_URL}/candidate/intro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userEmail,
          job_id: job.external_id ?? String(job.id),
          why_note: job.why || job.summary || "",
        }),
      });

      let data: unknown = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }

      const p = extractIntroApiPayload(data);

      if (isIntroGateBlocked(p)) {
        const missing =
          p.missingSignals.length > 0
            ? p.missingSignals
            : parseMissingFromGateMessage(p.message);
        const stored = missing.length > 0 ? missing : [];
        setIntroStatuses(prev => ({ ...prev, [job.id]: "needs_info" }));
        setIntroMissingByJob(prev => ({
          ...prev,
          [job.id]: stored,
        }));
        setWeakIntroModal({ job, missing: stored });
        return;
      }

      if (!res.ok) {
        throw new Error(p.message || `HTTP ${res.status}`);
      }

      setWeakIntroModal(prev => (prev && prev.job.id === job.id ? null : prev));

      if (p.alreadySent) {
        setIntroStatuses(prev => ({ ...prev, [job.id]: "already_sent" }));
      } else if (p.ok) {
        setIntroStatuses(prev => ({ ...prev, [job.id]: "sent" }));
      } else {
        setIntroStatuses(prev => ({ ...prev, [job.id]: "error" }));
        setIntroErrors(prev => ({ ...prev, [job.id]: p.message || "Something went wrong." }));
      }
    } catch (err) {
      setIntroStatuses(prev => ({ ...prev, [job.id]: "error" }));
      setIntroErrors(prev => ({ ...prev, [job.id]: err instanceof Error ? err.message : "Something went wrong." }));
    }
  }, [userEmail]);

  return (
    <div className="match-root">
      {weakIntroModal && (
        <WeakIntroModal
          job={weakIntroModal.job}
          missing={weakIntroModal.missing}
          userEmail={userEmail}
          introStatus={introStatuses[weakIntroModal.job.id] ?? "idle"}
          onClose={() => setWeakIntroModal(null)}
          onRetry={handleRequestIntro}
        />
      )}
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
          <div className="match-grid">
            <SkeletonCard delay={0} />
            <SkeletonCard delay={0.08} />
            <SkeletonCard delay={0.16} />
          </div>
        ) : jobs.length === 0 ? (
          <div className="match-empty">
            <p className="match-empty-title">No matches yet</p>
            <p className="match-empty-sub">
              Chat with Mitra to get your personalised shortlist.
            </p>
            <Link href="/chat" className="match-btn match-btn--primary">Start the conversation →</Link>
          </div>
        ) : (() => {
          const visibleJobs = jobs.filter(j => !dismissedIds.has(j.id));
          if (visibleJobs.length === 0) return (
            <div className="match-empty">
              <p className="match-empty-title">You&apos;ve reviewed all your matches</p>
              <p className="match-empty-sub">Chat with Mitra to discover more roles.</p>
              <Link href="/chat" className="match-btn match-btn--primary">Back to chat →</Link>
            </div>
          );
          const groups = groupAndSort(visibleJobs);
          const showHeaders = groups.length > 1 || groups[0]?.label !== "Today";
          let globalIdx = 0;
          return (
            <div className="match-grid">
              {groups.map(({ label, jobs: groupJobs }) => (
                <Fragment key={label}>
                  {showHeaders && (
                    <div className="match-date-header">
                      <span className="match-date-header-label">{label}</span>
                      <span className="match-date-header-count">
                        {groupJobs.length} role{groupJobs.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                  )}
                  {groupJobs.map((job) => {
                    const idx = globalIdx++;
                    return (
                      <JobCard
                        key={`${job.id}-${idx}`}
                        job={job}
                        idx={idx}
                        userEmail={userEmail}
                        introStatus={introStatuses[job.id] ?? "idle"}
                        introError={introErrors[job.id] ?? ""}
                        introMissing={introMissingByJob[job.id] ?? []}
                        onRequestIntro={handleRequestIntro}
                        onShowWeakIntro={() =>
                          setWeakIntroModal({ job, missing: introMissingByJob[job.id] ?? [] })
                        }
                        onDismiss={handleDismiss}
                      />
                    );
                  })}
                </Fragment>
              ))}
            </div>
          );
        })()}
      </main>
    </div>
  );
}
