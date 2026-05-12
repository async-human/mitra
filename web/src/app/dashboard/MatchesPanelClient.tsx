"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { introStatusMeta, isTerminalIntroStatus } from "./candidatePipeline";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface StoredCard { id: string; title: string; description: string; }

interface IntroBrief {
  job_id: number;
  status: string;
}

function matchesKey(email: string) {
  return `mitra-matches-${email}`;
}

function MatchesEmptyIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect x="4" y="10" width="32" height="22" rx="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 16h32" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="11" cy="13" r="1.5" fill="currentColor" />
      <circle cx="16" cy="13" r="1.5" fill="currentColor" />
      <path d="M12 24h8M12 28h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function MatchesPanelClient({ userEmail }: { userEmail: string }) {
  const [cards, setCards] = useState<StoredCard[] | null>(null);
  const [matchIds, setMatchIds] = useState<string>("");
  const [intros, setIntros] = useState<IntroBrief[] | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(matchesKey(userEmail))
        ?? localStorage.getItem("mitra-matches");
      if (raw) {
        const parsed: StoredCard[] = JSON.parse(raw);
        if (parsed.length > 0) {
          setCards(parsed);
          setMatchIds(parsed.map(c => c.id.replace(/^job_/, "")).join(","));
        }
      }
    } catch { /* localStorage unavailable or corrupt */ }
  }, [userEmail]);

  useEffect(() => {
    if (!userEmail) return;
    fetch(`${API_URL}/candidate/intros?session_id=${encodeURIComponent(userEmail)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: IntroBrief[]) => {
        if (Array.isArray(data)) setIntros(data.map((i) => ({ job_id: i.job_id, status: i.status })));
      })
      .catch(() => setIntros([]));
  }, [userEmail]);

  const introByJobId = useMemo(() => {
    const m = new Map<string, IntroBrief>();
    if (!intros) return m;
    for (const i of intros) m.set(String(i.job_id), i);
    return m;
  }, [intros]);

  if (cards && cards.length > 0) {
    const openRoles = cards.filter((c) => {
      const intro = introByJobId.get(c.id.replace(/^job_/, ""));
      return !intro || !isTerminalIntroStatus(intro.status);
    }).length;
    const badgeLabel =
      intros === null
        ? `${cards.length} saved`
        : openRoles < cards.length
        ? `${openRoles} open · ${cards.length - openRoles} wrapped up`
        : `${cards.length} saved`;

    return (
      <>
        <div className="dash-panel-head">
          <h3 className="dash-panel-title">Your matches</h3>
          <span className="dash-panel-badge dash-panel-badge--active">{badgeLabel}</span>
        </div>
        <div className="dash-matches-list">
          {cards.map((card) => {
            const parts = card.description.split(" · ").map(s => s.trim()).filter(Boolean);
            const fitPart = parts.find(p => p.includes("% fit") || p.includes("%fit")) ?? "";
            const company = parts[0] !== fitPart ? parts[0] : "";
            const intro = introByJobId.get(card.id.replace(/^job_/, ""));
            const meta = intro ? introStatusMeta(intro.status) : null;
            return (
              <div
                key={card.id}
                className={`dash-match-row${intro && isTerminalIntroStatus(intro.status) ? " dash-match-row--settled" : ""}`}
              >
                <div className="dash-match-av">{(company || card.title).slice(0, 2).toUpperCase()}</div>
                <div className="dash-match-info">
                  <span className="dash-match-role">{card.title}</span>
                  {company && <span className="dash-match-company">{company}</span>}
                </div>
                <div className="dash-match-meta">
                  {intro && meta && (
                    <span
                      className={`dash-match-intro-chip${meta.pulse ? " dash-match-intro-chip--pulse" : ""}`}
                      style={{ color: meta.color, background: meta.bg }}
                    >
                      {meta.label}
                    </span>
                  )}
                  {fitPart && <span className="dash-match-fit">{fitPart}</span>}
                </div>
              </div>
            );
          })}
        </div>
        <Link href={`/matches?ids=${matchIds}`} className="dash-matches-view-btn">
          View full shortlist →
        </Link>
      </>
    );
  }

  return (
    <>
      <div className="dash-panel-head">
        <h3 className="dash-panel-title">Your matches</h3>
        <span className="dash-panel-badge">0 saved</span>
      </div>
      <div className="dash-empty">
        <div className="dash-empty-icon"><MatchesEmptyIcon /></div>
        <p className="dash-empty-title">No matches yet</p>
        <p className="dash-empty-desc">
          Complete your chat with Mitra and we&apos;ll surface the roles built for someone like you.
        </p>
        <Link href="/chat" className="dash-empty-cta">
          Start the conversation →
        </Link>
      </div>
    </>
  );
}
