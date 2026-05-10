"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface StoredCard { id: string; title: string; description: string; }

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

  if (cards && cards.length > 0) {
    return (
      <>
        <div className="dash-panel-head">
          <h3 className="dash-panel-title">Your matches</h3>
          <span className="dash-panel-badge dash-panel-badge--active">{cards.length} active</span>
        </div>
        <div className="dash-matches-list">
          {cards.map((card, i) => {
            const parts = card.description.split(" · ").map(s => s.trim()).filter(Boolean);
            const fitPart = parts.find(p => p.includes("% fit") || p.includes("%fit")) ?? "";
            const company = parts[0] !== fitPart ? parts[0] : "";
            return (
              <div key={card.id} className="dash-match-row">
                <div className="dash-match-av">{(company || card.title).slice(0, 2).toUpperCase()}</div>
                <div className="dash-match-info">
                  <span className="dash-match-role">{card.title}</span>
                  {company && <span className="dash-match-company">{company}</span>}
                </div>
                {fitPart && <span className="dash-match-fit">{fitPart}</span>}
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
        <span className="dash-panel-badge">0 active</span>
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
