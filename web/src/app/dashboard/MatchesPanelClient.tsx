"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { introStatusMeta, isTerminalIntroStatus } from "./candidatePipeline";
import type { CandidateIntro } from "./introTypes";
import { deriveMatchCardsFromIntros, type StoredMatchCard } from "./deriveMatchCards";

function parseMatchCardDescription(description: string) {
  const parts = description.split(" · ").map((s) => s.trim()).filter(Boolean);
  const fitPart = parts.find((p) => /%\s*fit/i.test(p)) ?? "";
  const company = parts[0] && parts[0] !== fitPart ? parts[0] : "";
  const tagline = parts.filter((p) => p !== company && p !== fitPart).join(" · ");
  return { company, fitPart, tagline };
}

function truncateText(s: string, max: number) {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1).trimEnd()}…`;
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

export function MatchesPanelClient({
  userEmail,
  intros,
  introsLoaded,
}: {
  userEmail: string;
  intros: CandidateIntro[];
  introsLoaded: boolean;
}) {
  const [cards, setCards] = useState<StoredCard[] | null>(null);
  const [matchIds, setMatchIds] = useState<string>("");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(matchesKey(userEmail))
        ?? localStorage.getItem("mitra-matches");
      if (raw) {
        const parsed: StoredMatchCard[] = JSON.parse(raw);
        if (parsed.length > 0) {
          setCards(parsed);
          setMatchIds(parsed.map(c => c.id.replace(/^job_/, "")).join(","));
          return;
        }
      }
    } catch { /* localStorage unavailable or corrupt */ }

    if (introsLoaded && intros.length > 0) {
      const derived = deriveMatchCardsFromIntros(intros);
      if (derived.length > 0) {
        setCards(derived);
        setMatchIds(derived.map(c => c.id.replace(/^job_/, "")).join(","));
        try {
          localStorage.setItem(matchesKey(userEmail), JSON.stringify(derived));
        } catch { /* ignore */ }
      }
    }
  }, [userEmail, intros, introsLoaded]);

  const introByJobId = useMemo(() => {
    const m = new Map<string, { job_id: number; status: string }>();
    if (!introsLoaded) return m;
    for (const i of intros) m.set(String(i.job_id), i);
    return m;
  }, [intros, introsLoaded]);

  if (cards && cards.length > 0) {
    const openRoles = cards.filter((c) => {
      const intro = introByJobId.get(c.id.replace(/^job_/, ""));
      return !intro || !isTerminalIntroStatus(intro.status);
    }).length;
    const badgeLabel =
      !introsLoaded
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
            const { company, fitPart, tagline } = parseMatchCardDescription(card.description);
            const whyLine = card.why?.trim();
            const intro = introByJobId.get(card.id.replace(/^job_/, ""));
            const meta = intro ? introStatusMeta(intro.status) : null;
            const jobIdParam = encodeURIComponent(card.id.replace(/^job_/, ""));
            return (
              <Link
                key={card.id}
                href={`/matches?ids=${jobIdParam}`}
                className={`dash-match-row-link${intro && isTerminalIntroStatus(intro.status) ? " dash-match-row-link--settled" : ""}`}
              >
                <div
                  className={`dash-match-row${intro && isTerminalIntroStatus(intro.status) ? " dash-match-row--settled" : ""}`}
                >
                  <div className="dash-match-av">{(company || card.title).slice(0, 2).toUpperCase()}</div>
                  <div className="dash-match-info">
                    <span className="dash-match-role">{card.title}</span>
                    {company ? <span className="dash-match-company">{company}</span> : null}
                    {whyLine ? (
                      <span className="dash-match-why">{truncateText(whyLine, 140)}</span>
                    ) : tagline ? (
                      <span className="dash-match-tagline">{truncateText(tagline, 120)}</span>
                    ) : null}
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
                    {fitPart ? <span className="dash-match-fit">{fitPart}</span> : null}
                  </div>
                </div>
              </Link>
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
