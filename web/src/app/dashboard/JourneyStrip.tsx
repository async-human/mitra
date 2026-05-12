"use client";

import { useState, useEffect } from "react";
import { WhatsAppIcon } from "@/components/icons";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

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

function IntroIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
      <path d="M1.5 4.5h12a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-12a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.4" />
      <path d="M1 5.5l6.5 4.5L14 5.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

type StepState = "done" | "current" | "locked";

export function JourneyStrip({ userEmail }: { userEmail: string }) {
  const [hasMatches, setHasMatches] = useState(false);
  const [hasIntros, setHasIntros] = useState(false);

  useEffect(() => {
    try {
      const raw =
        localStorage.getItem(`mitra-matches-${userEmail}`) ??
        localStorage.getItem("mitra-matches");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) setHasMatches(true);
      }
    } catch { /* localStorage unavailable */ }

    if (!userEmail) return;
    fetch(`${API_URL}/candidate/intros?session_id=${encodeURIComponent(userEmail)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown[]) => {
        if (Array.isArray(data) && data.length > 0) setHasIntros(true);
      })
      .catch(() => {});
  }, [userEmail]);

  const step1: StepState = "done";
  const step2: StepState = hasMatches ? "done" : "current";
  const step3: StepState = hasIntros ? "done" : hasMatches ? "current" : "locked";

  return (
    <section className="dash-journey">
      <div className="dash-journey-inner">

        <div className={`dash-step dash-step--${step1}`}>
          <div className={`dash-step-icon dash-step-icon--${step1}`}>
            <CheckIcon />
          </div>
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
            <div className="dash-step-label">
              {step2 === "current" ? "Step 2 — Now" : "Step 2"}
            </div>
            <div className="dash-step-title">Chat with Mitra</div>
            <div className="dash-step-desc">
              {step2 === "done"
                ? "Done — we have everything we need."
                : "A 2-minute conversation — your experience, what you want, what you won’t compromise on."}
            </div>
          </div>
        </div>

        <div className="dash-step-line" />

        <div className={`dash-step dash-step--${step3}`}>
          <div className={`dash-step-icon dash-step-icon--${step3}`}>
            {step3 === "done" ? <CheckIcon /> : step3 === "current" ? <IntroIcon /> : <LockIcon />}
          </div>
          <div className="dash-step-body">
            <div className="dash-step-label">
              {step3 === "current" ? "Step 3 — Now" : "Step 3"}
            </div>
            <div className="dash-step-title">Receive your matches</div>
            <div className="dash-step-desc">
              {step3 === "done"
                ? "Introductions sent — check your pipeline below."
                : step3 === "current"
                ? "Your shortlist is ready. Introductions are being sent."
                : "3–5 curated introductions, each with a clear reason why. No ghosting, ever."}
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
