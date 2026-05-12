"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface InterviewDetails {
  scheduled_at?: string;
  format?: string;
  link?: string;
  notes?: string;
}
interface OfferDetails {
  salary_lpa?: number;
  equity_percent?: number;
  start_date?: string;
  notes?: string;
}
interface IntroSummary {
  intro_id: number;
  job_id: number;
  job_title: string;
  company: string;
  status: string;
  sent_at: string | null;
  interview_details?: InterviewDetails | null;
  offer_details?: OfferDetails | null;
}

const STATUS_META: Record<string, { label: string; color: string; bg: string; dot: string; pulse?: boolean }> = {
  sent:         { label: "Intro sent",         color: "#059669", bg: "#ECFDF5", dot: "#34D399" },
  acknowledged: { label: "Interested ✦",       color: "#7C3AED", bg: "#F5F3FF", dot: "#A78BFA", pulse: true },
  interview:    { label: "Interview booked",   color: "#D97706", bg: "#FFFBEB", dot: "#FCD34D", pulse: true },
  offer:        { label: "Offer received",     color: "#059669", bg: "#ECFDF5", dot: "#6EE7B7", pulse: true },
  hired:        { label: "Hired 🎉",           color: "#059669", bg: "#ECFDF5", dot: "#6EE7B7" },
  declined:     { label: "Not a fit",          color: "#6B7280", bg: "#F3F4F6", dot: "#D1D5DB" },
  ghosted:      { label: "Awaiting reply",     color: "#9CA3AF", bg: "#F9FAFB", dot: "#E5E7EB" },
};

function statusMeta(status: string) {
  return STATUS_META[status] ?? { label: status, color: "#6B7280", bg: "#F3F4F6", dot: "#D1D5DB" };
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function IntrosEmptyIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path d="M6 10h28a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 12l16 11 16-11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function formatDateTime(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit", hour12: true,
  });
}

function IntroDetailModal({ intro, onClose }: { intro: IntroSummary; onClose: () => void }) {
  const meta = statusMeta(intro.status);
  const iv = intro.interview_details;
  const of = intro.offer_details;

  return (
    <div className="dash-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="dash-modal" onClick={e => e.stopPropagation()}>
        <div className="dash-modal-header">
          <div>
            <p className="dash-modal-company">{intro.company}</p>
            <h2 className="dash-modal-role">{intro.job_title}</h2>
          </div>
          <button className="dash-modal-close" onClick={onClose} aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          </button>
        </div>

        <div className="dash-modal-status" style={{ color: meta.color, background: meta.bg }}>
          <span className="dash-intro-dot" style={{ background: meta.dot }} />
          {meta.label}
          {intro.sent_at && <span className="dash-modal-status-date">· Intro sent {formatDate(intro.sent_at)}</span>}
        </div>

        {/* Interview details */}
        {intro.status === "interview" && (
          <div className="dash-modal-section">
            <p className="dash-modal-section-title">Interview details</p>
            {iv?.scheduled_at ? (
              <div className="dash-modal-facts">
                <div className="dash-modal-fact">
                  <span className="dash-modal-fact-label">When</span>
                  <span className="dash-modal-fact-value">{formatDateTime(iv.scheduled_at)}</span>
                </div>
                {iv.format && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Format</span>
                    <span className="dash-modal-fact-value" style={{ textTransform: "capitalize" }}>{iv.format === "in-person" ? "In-person" : iv.format === "video" ? "Video call" : "Phone call"}</span>
                  </div>
                )}
                {iv.link && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Link</span>
                    <a href={iv.link} target="_blank" rel="noopener noreferrer" className="dash-modal-link">{iv.link}</a>
                  </div>
                )}
                {iv.notes && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Notes</span>
                    <span className="dash-modal-fact-value">{iv.notes}</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="dash-modal-pending">Interview details will appear here once the founder confirms the time.</p>
            )}
          </div>
        )}

        {/* Offer details */}
        {intro.status === "offer" && (
          <div className="dash-modal-section">
            <p className="dash-modal-section-title">Offer details</p>
            {of ? (
              <div className="dash-modal-facts">
                {of.salary_lpa && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Salary</span>
                    <span className="dash-modal-fact-value">₹{of.salary_lpa}L / year</span>
                  </div>
                )}
                {of.equity_percent != null && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Equity</span>
                    <span className="dash-modal-fact-value">{of.equity_percent}%</span>
                  </div>
                )}
                {of.start_date && (
                  <div className="dash-modal-fact">
                    <span className="dash-modal-fact-label">Start date</span>
                    <span className="dash-modal-fact-value">{formatDate(of.start_date)}</span>
                  </div>
                )}
                {of.notes && (
                  <div className="dash-modal-fact dash-modal-fact--notes">
                    <span className="dash-modal-fact-label">From the founder</span>
                    <span className="dash-modal-fact-value">{of.notes}</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="dash-modal-pending">Offer details will appear here once shared by the founder.</p>
            )}
          </div>
        )}

        <div className="dash-modal-footer">
          <p className="dash-modal-footer-note">Questions? Chat with Mitra — we&apos;ll help you decide.</p>
          <Link href="/chat" className="dash-modal-chat-btn" onClick={onClose}>Chat with Mitra →</Link>
        </div>
      </div>
    </div>
  );
}

export function IntrosPanelClient({ userEmail }: { userEmail: string }) {
  const [intros, setIntros] = useState<IntroSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<IntroSummary | null>(null);

  useEffect(() => {
    if (!userEmail) { setLoading(false); return; }
    fetch(`${API_URL}/candidate/intros?session_id=${encodeURIComponent(userEmail)}`)
      .then(r => r.ok ? r.json() : [])
      .then((data: IntroSummary[]) => setIntros(data))
      .catch(() => setIntros([]))
      .finally(() => setLoading(false));
  }, [userEmail]);

  const count = intros?.length ?? 0;

  return (
    <>
      {selected && <IntroDetailModal intro={selected} onClose={() => setSelected(null)} />}

      <div className="dash-panel-head">
        <h3 className="dash-panel-title">Introductions</h3>
        {loading ? (
          <span className="dash-panel-badge">—</span>
        ) : (
          <span className={`dash-panel-badge${count > 0 ? " dash-panel-badge--active" : ""}`}>
            {count} sent
          </span>
        )}
      </div>

      {loading && (
        <div className="dash-intros-skeleton">
          {[70, 55, 65].map((w, i) => (
            <div key={i} className="dash-intro-sk-row">
              <span className="dash-intro-sk-av" />
              <div className="dash-intro-sk-lines">
                <span className="dash-intro-sk-line" style={{ width: `${w}%` }} />
                <span className="dash-intro-sk-line" style={{ width: "45%" }} />
              </div>
              <span className="dash-intro-sk-badge" />
            </div>
          ))}
        </div>
      )}

      {!loading && count > 0 && (
        <div className="dash-intros-list">
          {intros!.map(intro => {
            const meta = statusMeta(intro.status);
            const isClickable = ["interview", "offer", "hired"].includes(intro.status);
            return (
              <button
                key={intro.intro_id}
                className={`dash-intro-row${isClickable ? " dash-intro-row--clickable" : ""}`}
                onClick={() => isClickable && setSelected(intro)}
                type="button"
              >
                <div className="dash-intro-av">
                  {intro.company.slice(0, 2).toUpperCase()}
                </div>
                <div className="dash-intro-info">
                  <span className="dash-intro-role">{intro.job_title}</span>
                  <span className="dash-intro-company">{intro.company}</span>
                </div>
                <div className="dash-intro-right">
                  <span
                    className={`dash-intro-status-badge${meta.pulse ? " dash-intro-status-badge--pulse" : ""}`}
                    style={{ color: meta.color, background: meta.bg }}
                  >
                    <span className={`dash-intro-dot${meta.pulse ? " dash-intro-dot--pulse" : ""}`} style={{ background: meta.dot }} />
                    {meta.label}
                  </span>
                  {intro.sent_at && <span className="dash-intro-date">{formatDate(intro.sent_at)}</span>}
                  {isClickable && <span className="dash-intro-chevron">›</span>}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {!loading && count === 0 && (
        <div className="dash-empty">
          <div className="dash-empty-icon"><IntrosEmptyIcon /></div>
          <p className="dash-empty-title">No intros yet</p>
          <p className="dash-empty-desc">
            Once you request an intro from your shortlist, it appears here with live status.
          </p>
          <Link href="/matches" className="dash-empty-cta">
            View your shortlist →
          </Link>
        </div>
      )}
    </>
  );
}
