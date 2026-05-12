"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { WhatsAppIcon } from "@/components/icons";
import { MatchesPanelClient } from "./MatchesPanelClient";
import { IntrosPanelClient } from "./IntrosPanelClient";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/* ── Icons ─────────────────────────────────────────────────────────────── */

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <rect x="2" y="6" width="9" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4 6V4.5a2.5 2.5 0 1 1 5 0V6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
      <path d="M14.5 9.5a6 6 0 0 1-8.5 5.4L2 16l1.1-4A6 6 0 1 1 14.5 9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ActivityIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M1 9h3.5l2-6 5 12 2.5-6H17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IntroIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path d="M1.5 4.5h12a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-12a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.4" />
      <path d="M1 5.5l6.5 4.5L14 5.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="3" y="4.5" width="14" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 8h14M7 2.8v3M13 2.8v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/* ── Types ──────────────────────────────────────────────────────────────── */

interface StoredCard { id: string; title: string; description: string; }
interface IntroSummary {
  intro_id: number; job_id: number; job_title: string;
  company: string; status: string; sent_at: string | null;
}
type StepState = "done" | "current" | "locked";

type DashboardUpdateKind = "offer" | "interview" | "hired" | "intros" | "shortlist" | "default";

interface DashboardUpdate {
  kind: DashboardUpdateKind;
  label: string;
  headline: string;
  detail?: string;
}

/* ── Helpers ────────────────────────────────────────────────────────────── */

function getDashboardUpdate(matches: StoredCard[], intros: IntroSummary[]): DashboardUpdate {
  const offers = intros.filter((i) => i.status === "offer");
  if (offers.length > 0) {
    const company = offers[0].company;
    const headline =
      offers.length === 1
        ? `You have an offer from ${company}`
        : `${offers.length} offers received — including ${company}`;
    return {
      kind: "offer",
      label: offers.length === 1 ? "Latest update" : "Latest updates",
      headline,
      detail: "Review your introductions below.",
    };
  }
  const interviews = intros.filter((i) => i.status === "interview");
  if (interviews.length === 1) {
    return {
      kind: "interview",
      label: "Interview booked",
      headline: `Up next with ${interviews[0].company}`,
      detail: "Your pipeline is moving — details are in introductions.",
    };
  }
  if (interviews.length > 1) {
    return {
      kind: "interview",
      label: "Interviews booked",
      headline: `${interviews.length} interviews on your calendar`,
      detail: "Things are moving fast — keep an eye on your introductions.",
    };
  }
  const hiredList = intros.filter((i) => i.status === "hired");
  if (hiredList.length > 0 && offers.length === 0 && interviews.length === 0) {
    const stillOpen = intros.some((i) => !["hired", "declined"].includes(i.status));
    return {
      kind: "hired",
      label: stillOpen ? "Great news — pipeline still open" : "Great news",
      headline:
        hiredList.length === 1
          ? `You're hired at ${hiredList[0].company}`
          : `${hiredList.length} offers you've accepted`,
      detail: stillOpen
        ? "Other introductions below are still in progress if you're comparing options."
        : "Each introduction is summarized in the list below.",
    };
  }
  if (intros.length > 0) {
    return {
      kind: "intros",
      label: "Pipeline",
      headline: `${intros.length} introduction${intros.length !== 1 ? "s" : ""} in flight`,
      detail: "Track status below.",
    };
  }
  if (matches.length > 0) {
    return {
      kind: "shortlist",
      label: "Shortlist",
      headline: "Your shortlist is ready",
      detail: "Mitra is making introductions on your behalf.",
    };
  }
  return {
    kind: "default",
    label: "",
    headline: "Your next move starts with one honest conversation.",
  };
}

function DashboardUpdateNotice({ update }: { update: DashboardUpdate }) {
  if (update.kind === "default") {
    return <p className="dash-greeting-sub">{update.headline}</p>;
  }

  const icon =
    update.kind === "offer" || update.kind === "hired" ? (
      <CheckIcon />
    ) : update.kind === "interview" ? (
      <CalendarIcon />
    ) : (
      <IntroIcon />
    );

  return (
    <div className={`dash-update dash-update--${update.kind}`} role="status">
      <div className="dash-update-icon" aria-hidden="true">
        {icon}
      </div>
      <div className="dash-update-body">
        <p className="dash-update-label">{update.label}</p>
        <p className="dash-update-headline">{update.headline}</p>
        {update.detail ? <p className="dash-update-detail">{update.detail}</p> : null}
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────────── */

export function DashboardClient({
  userEmail, firstName, greeting, waHref,
}: {
  userEmail: string;
  firstName: string;
  greeting: string;
  waHref: string;
}) {
  const [matches, setMatches] = useState<StoredCard[]>([]);
  const [intros, setIntros] = useState<IntroSummary[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw =
        localStorage.getItem(`mitra-matches-${userEmail}`) ??
        localStorage.getItem("mitra-matches");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setMatches(parsed);
      }
    } catch { /* ignore */ }

    fetch(`${API_URL}/candidate/intros?session_id=${encodeURIComponent(userEmail)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: IntroSummary[]) => { if (Array.isArray(data)) setIntros(data); })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, [userEmail]);

  const hasMatches = matches.length > 0;
  const hasIntros = intros.length > 0;

  const offerCount    = intros.filter(i => i.status === "offer").length;
  const interviewCount = intros.filter(i => i.status === "interview").length;
  const hiredCount = intros.filter((i) => i.status === "hired").length;

  const pipelineCardQuiet =
    offerCount > 0 ||
    interviewCount > 0 ||
    (hiredCount > 0 && hasIntros);

  const step2: StepState = hasMatches ? "done" : "current";
  const step3: StepState = hasIntros ? "done" : hasMatches ? "current" : "locked";

  const dashboardUpdate = getDashboardUpdate(matches, intros);

  return (
    <>
      {/* ── Greeting ─────────────────────────────────────────────────────── */}
      <section className="dash-greeting">
        <p className="dash-greeting-eyebrow">{greeting}</p>
        <h1 className="dash-greeting-h1">{firstName}.</h1>
        <DashboardUpdateNotice update={dashboardUpdate} />
      </section>

      {/* ── Journey strip (only before chatting) ─────────────────────────── */}
      {!hasMatches && (
        <section className="dash-journey">
          <div className="dash-journey-inner">

            <div className="dash-step dash-step--done">
              <div className="dash-step-icon dash-step-icon--done"><CheckIcon /></div>
              <div className="dash-step-body">
                <div className="dash-step-label">Step 1</div>
                <div className="dash-step-title">Signed in</div>
                <div className="dash-step-desc">You&apos;re here. That&apos;s the start.</div>
              </div>
            </div>

            <div className="dash-step-line" />

            <div className={`dash-step dash-step--${step2}`}>
              <div className={`dash-step-icon dash-step-icon--${step2}`}>
                {step2 === "done" ? <CheckIcon /> : <WhatsAppIcon size={16} />}
              </div>
              <div className="dash-step-body">
                <div className="dash-step-label">{step2 === "current" ? "Step 2 — Now" : "Step 2"}</div>
                <div className="dash-step-title">Chat with Mitra</div>
                <div className="dash-step-desc">A 2-minute conversation — your experience, what you want, what you won&apos;t compromise on.</div>
              </div>
            </div>

            <div className="dash-step-line" />

            <div className={`dash-step dash-step--${step3}`}>
              <div className={`dash-step-icon dash-step-icon--${step3}`}>
                {step3 === "done" ? <CheckIcon /> : step3 === "current" ? <IntroIcon /> : <LockIcon />}
              </div>
              <div className="dash-step-body">
                <div className="dash-step-label">{step3 === "current" ? "Step 3 — Now" : "Step 3"}</div>
                <div className="dash-step-title">Receive your matches</div>
                <div className="dash-step-desc">3–5 curated introductions, each with a clear reason why. No ghosting, ever.</div>
              </div>
            </div>

          </div>
        </section>
      )}

      {/* ── One-time reassurance (matches ready, intros not started — avoids repeating counts shown in columns) ─ */}
      {hasMatches && loaded && !hasIntros && (
        <div className="dash-onboarding-badge dash-onboarding-badge--solo">
          <span className="dash-onboarding-icon"><CheckIcon /></span>
          <span>You&apos;re set — introductions will appear in the column on the right as we reach out.</span>
        </div>
      )}

      {/* ── Action section ───────────────────────────────────────────────── */}
      {!hasMatches ? (
        /* Pre-chat: prominent start CTA */
        <section className="dash-cta-section">
          <div className="dash-cta-card">
            <div className="dash-cta-text">
              <h2 className="dash-cta-title">Ready to start?</h2>
              <p className="dash-cta-sub">
                Chat with Mitra right here — tell us what you&apos;re looking for. Takes 2 minutes. No CV needed.
              </p>
            </div>
            <div className="dash-cta-btns">
              <Link href="/chat" className="dash-wa-btn">
                <ChatIcon />
                Chat with Mitra
              </Link>
              <a href={waHref} target="_blank" rel="noopener noreferrer" className="dash-wa-btn dash-wa-btn--secondary">
                <WhatsAppIcon size={17} />
                Open in WhatsApp
              </a>
            </div>
          </div>
          <p className="dash-cta-note">Free for candidates · Always</p>
        </section>
      ) : (
        /* Post-chat: pipeline status card */
        <div
          className={`dash-pipeline-card${pipelineCardQuiet ? " dash-pipeline-card--quiet" : ""}`}
        >
          <div className="dash-pipeline-left">
            <div className="dash-pipeline-icon">
              <ActivityIcon />
            </div>
            <div>
              <p className="dash-pipeline-title">
                {pipelineCardQuiet
                  ? "Your search"
                  : hasIntros
                  ? "Pipeline active"
                  : "Introductions in progress"}
              </p>
              <p className="dash-pipeline-sub">
                {offerCount > 0 ? (
                  <>Update preferences if your situation changes — details stay in Introductions.</>
                ) : interviewCount > 0 ? (
                  <>
                    {intros.length > interviewCount
                      ? `${intros.length - interviewCount} more intro${intros.length - interviewCount !== 1 ? "s" : ""} still in motion · `
                      : ""}
                    Full schedule lives in Introductions.
                  </>
                ) : hiredCount > 0 && offerCount === 0 && interviewCount === 0 ? (
                  <>Update Mitra if your plans change — everything else lives in Introductions.</>
                ) : hasIntros ? (
                  `${intros.length} introduction${intros.length !== 1 ? "s" : ""} tracked below.`
                ) : (
                  "Mitra is reaching out to companies on your behalf — check back soon."
                )}
              </p>
            </div>
          </div>
          <Link href="/chat?intent=update" className="dash-pipeline-update">
            Update preferences →
          </Link>
        </div>
      )}

      {/* ── Panels ───────────────────────────────────────────────────────── */}
      <section className="dash-panels">
        <div className="dash-panel">
          <MatchesPanelClient userEmail={userEmail} />
        </div>
        <div className="dash-panel">
          <IntrosPanelClient userEmail={userEmail} />
        </div>
      </section>
    </>
  );
}
