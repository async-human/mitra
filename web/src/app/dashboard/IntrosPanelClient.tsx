"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface IntroSummary {
  intro_id: number;
  job_id: number;
  job_title: string;
  company: string;
  status: string;
  sent_at: string | null;
}

const STATUS_META: Record<string, { label: string; color: string; dot: string }> = {
  sent:         { label: "Intro sent",         color: "var(--teal)",    dot: "#34D399" },
  acknowledged: { label: "Founder replied",     color: "#7C3AED",       dot: "#A78BFA" },
  interview:    { label: "Interview booked",    color: "#D97706",       dot: "#FCD34D" },
  offer:        { label: "Offer received",      color: "#059669",       dot: "#6EE7B7" },
  hired:        { label: "Hired 🎉",            color: "#059669",       dot: "#6EE7B7" },
  declined:     { label: "Not moving forward",  color: "var(--ink-muted)", dot: "#9CA3AF" },
  ghosted:      { label: "Awaiting reply",      color: "var(--ink-muted)", dot: "#D1D5DB" },
};

function statusMeta(status: string) {
  return STATUS_META[status] ?? { label: status, color: "var(--ink-muted)", dot: "#D1D5DB" };
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

export function IntrosPanelClient({ userEmail }: { userEmail: string }) {
  const [intros, setIntros] = useState<IntroSummary[] | null>(null);
  const [loading, setLoading] = useState(true);

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
            return (
              <Link
                key={intro.intro_id}
                href={`/matches`}
                className="dash-intro-row"
              >
                {/* Company avatar */}
                <div className="dash-intro-av">
                  {intro.company.slice(0, 2).toUpperCase()}
                </div>

                {/* Info */}
                <div className="dash-intro-info">
                  <span className="dash-intro-role">{intro.job_title}</span>
                  <span className="dash-intro-company">{intro.company}</span>
                </div>

                {/* Status + date */}
                <div className="dash-intro-right">
                  <span className="dash-intro-status" style={{ color: meta.color }}>
                    <span className="dash-intro-dot" style={{ background: meta.dot }} />
                    {meta.label}
                  </span>
                  {intro.sent_at && (
                    <span className="dash-intro-date">{formatDate(intro.sent_at)}</span>
                  )}
                </div>
              </Link>
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
