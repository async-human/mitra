"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const AUTO_MS = 4000;

type PanelProps = { active: boolean };

function IconChat() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v7a2 2 0 01-2 2H7l-4 3V5z" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="5.5" />
      <path d="M16 16l-3-3" />
    </svg>
  );
}

function IconArrow() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 10h12M11 5l5 5-5 5" />
    </svg>
  );
}

function IconDoc() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="12" height="16" rx="2" />
      <path d="M8 7h4M8 10h4M8 13h2" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="7" r="3" />
      <path d="M2 17c0-3.314 2.686-5 6-5s6 1.686 6 5" />
      <path d="M14 5a3 3 0 010 6M18 17c0-2.5-1.5-4-4-4" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="8" />
      <path d="M6.5 10.5l2.5 2.5 4.5-5" />
    </svg>
  );
}

function CandidateSignalsPanel({ active }: PanelProps) {
  const signals = [
    "Ownership · wants end-to-end infra",
    "Stage · Series A–B fintech",
    "Stack · Go, Kubernetes, Postgres",
    "Motivation · tired of maintenance work",
  ];
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Signal extraction</span>
        <span className={s.hiwV3PanelLive}>
          <span className={s.hiwV3PanelLiveDot} />
          Live
        </span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={s.hiwV3ChatMini}>
          <div className={s.hiwV3ChatBubbleIn}>What would a great role look like in 12 months?</div>
          <div className={s.hiwV3ChatBubbleOut}>Own infra at a Series A fintech — Go, K8s</div>
        </div>
        <div className={s.hiwV3SignalList}>
          {signals.map((sig, i) => (
            <div
              key={sig}
              className={`${s.hiwV3Signal} ${active ? s.hiwV3SignalIn : ""}`}
              style={{ "--sig-delay": `${0.15 + i * 0.12}s` } as React.CSSProperties}
            >
              <span className={s.hiwV3SignalDot} />
              {sig}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CandidateMatchPanel({ active }: PanelProps) {
  const dims = [
    { label: "Stack fit", pct: 98 },
    { label: "Stage fit", pct: 92 },
    { label: "Salary align", pct: 100 },
    { label: "Motivation", pct: 89 },
    { label: "Ownership", pct: 95 },
  ];
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Fit scoring</span>
        <span className={s.hiwV3PanelScore}>94% match</span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={s.hiwV3MatchHeader}>
          <div className={s.hiwV3MatchLogo}>S</div>
          <div>
            <div className={s.hiwV3MatchCo}>Setu · Senior Platform Engineer</div>
            <div className={s.hiwV3MatchMeta}>Series B · Fintech · ₹42–58L</div>
          </div>
        </div>
        <div className={s.hiwV3MatchDims}>
          {dims.map(({ label, pct }, i) => (
            <div key={label} className={s.hiwV3MatchRow}>
              <span className={s.hiwV3MatchLabel}>{label}</span>
              <div className={s.hiwV3MatchBarTrack}>
                <div
                  className={`${s.hiwV3MatchBarFill} ${active ? s.hiwV3MatchBarGrow : ""}`}
                  style={{ "--pct": `${pct}%`, "--bar-delay": `${i * 0.08}s` } as React.CSSProperties}
                />
              </div>
              <span className={s.hiwV3MatchPct}>{pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CandidateIntroPanel({ active }: PanelProps) {
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Warm intro</span>
        <span className={s.hiwV3PanelScore}>90%+ reply rate</span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={`${s.hiwV3IntroCard} ${active ? s.hiwV3IntroCardIn : ""}`}>
          <div className={s.hiwV3IntroFrom}>
            <span className={s.hiwV3IntroAv}>M</span>
            <div>
              <div className={s.hiwV3IntroName}>Mitra → Rahul · Setu</div>
              <div className={s.hiwV3IntroSub}>Founder already briefed</div>
            </div>
          </div>
          <p className={s.hiwV3IntroMsg}>
            Introducing Harshal — 6 yrs platform at Razorpay, wants ownership at a 30–50 person fintech.
            Stack: Go, K8s. Salary: ₹48–55L. Expecting your message.
          </p>
          <div className={s.hiwV3IntroReply}>
            <span className={s.hiwV3IntroReplyAv}>R</span>
            <p>&ldquo;This is exactly who we&rsquo;ve been looking for. Thursday at 10?&rdquo;</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function CompanyBriefPanel({ active }: PanelProps) {
  const reqs = [
    "Owns backend infra end-to-end",
    "Go or Rust · ex-fintech preferred",
    "30–50 person stage · high ownership",
    "90-day bar: ships without hand-holding",
  ];
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Role brief</span>
        <span className={s.hiwV3PanelLive}>
          <span className={s.hiwV3PanelLiveDot} />
          Parsing
        </span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={s.hiwV3ChatMini}>
          <div className={s.hiwV3ChatBubbleIn}>What does great look like in 90 days?</div>
          <div className={s.hiwV3ChatBubbleOut}>Owns all backend infra end-to-end</div>
        </div>
        <div className={s.hiwV3SignalList}>
          {reqs.map((req, i) => (
            <div
              key={req}
              className={`${s.hiwV3Signal} ${active ? s.hiwV3SignalIn : ""}`}
              style={{ "--sig-delay": `${0.15 + i * 0.12}s` } as React.CSSProperties}
            >
              <span className={s.hiwV3SignalDot} />
              {req}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CompanyRankPanel({ active }: PanelProps) {
  const candidates = [
    { initials: "PM", name: "Priya M.", meta: "5 yrs · Razorpay infra", fit: 94 },
    { initials: "AK", name: "Arjun K.", meta: "4 yrs · Platform · Setu", fit: 88 },
    { initials: "NR", name: "Nisha R.", meta: "3 yrs · Backend · CRED", fit: 76 },
  ];
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Ranked shortlist</span>
        <span className={s.hiwV3PanelScore}>3 qualified</span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={s.hiwV3RankList}>
          {candidates.map((c, i) => (
            <div
              key={c.initials}
              className={`${s.hiwV3RankRow} ${active ? s.hiwV3RankRowIn : ""}`}
              style={{ "--rank-delay": `${0.1 + i * 0.14}s` } as React.CSSProperties}
            >
              <span className={s.hiwV3RankAv}>{c.initials}</span>
              <div className={s.hiwV3RankInfo}>
                <div className={s.hiwV3RankName}>{c.name}</div>
                <div className={s.hiwV3RankMeta}>{c.meta}</div>
                <div className={s.hiwV3RankBarTrack}>
                  <div
                    className={`${s.hiwV3RankBarFill} ${active ? s.hiwV3MatchBarGrow : ""}`}
                    style={{ "--pct": `${c.fit}%`, "--bar-delay": `${0.2 + i * 0.1}s` } as React.CSSProperties}
                  />
                </div>
              </div>
              <span className={s.hiwV3RankPct}>{c.fit}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CompanyIntroPanel({ active }: PanelProps) {
  return (
    <div className={s.hiwV3Panel}>
      <div className={s.hiwV3PanelChrome}>
        <span>Intro with context</span>
        <span className={s.hiwV3PanelScore}>Full portrait attached</span>
      </div>
      <div className={s.hiwV3PanelBody}>
        <div className={`${s.hiwV3IntroCard} ${active ? s.hiwV3IntroCardIn : ""}`}>
          <div className={s.hiwV3IntroFrom}>
            <span className={s.hiwV3IntroAv}>M</span>
            <div>
              <div className={s.hiwV3IntroName}>Mitra → You</div>
              <div className={s.hiwV3IntroSub}>Priya M. · 94% fit</div>
            </div>
          </div>
          <p className={s.hiwV3IntroMsg}>
            5 yrs infra at Razorpay. Motivated by ownership at your stage — not just comp.
            Notice: 45 days. She knows your stack and is expecting your message.
          </p>
          <div className={s.hiwV3IntroActions}>
            <span className={s.hiwV3IntroBtn}>Interested →</span>
            <span className={s.hiwV3IntroBtnGhost}>Pass</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const STEPS = {
  candidate: [
    {
      num: "01",
      Icon: IconChat,
      title: "Mitra listens — and extracts signals",
      Panel: CandidateSignalsPanel,
    },
    {
      num: "02",
      Icon: IconSearch,
      title: "Matches scored on what matters",
      Panel: CandidateMatchPanel,
    },
    {
      num: "03",
      Icon: IconArrow,
      title: "Warm intro that lands",
      Panel: CandidateIntroPanel,
    },
  ],
  company: [
    {
      num: "01",
      Icon: IconDoc,
      title: "Brief once — Mitra remembers",
      Panel: CompanyBriefPanel,
    },
    {
      num: "02",
      Icon: IconUsers,
      title: "Candidates ranked by intent",
      Panel: CompanyRankPanel,
    },
    {
      num: "03",
      Icon: IconCheck,
      title: "Intros with full context",
      Panel: CompanyIntroPanel,
    },
  ],
};

const TITLE = {
  candidate: "A companion that gets smarter the more you talk.",
  company: "From brief to shortlist. Sharper every time.",
};

export function HowItWorksV3({ audience }: { audience: V2Audience }) {
  const steps = STEPS[audience];
  const [activeTab, setActiveTab] = useState(0);
  const [inView, setInView] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0.2 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const advance = useCallback(() => {
    setActiveTab((prev) => (prev + 1) % steps.length);
  }, [steps.length]);

  useEffect(() => {
    if (!inView) return;
    timerRef.current = setTimeout(advance, AUTO_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [activeTab, inView, advance, audience]);

  const ActivePanel = steps[activeTab].Panel;

  return (
    <section className={s.sectionWrap} id="how-it-works" ref={sectionRef}>
      <div className={s.sectionInner} key={audience}>
        <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
          A different approach
        </p>
        <h2 className={`${s.sectionTitle} ${s.fadeUp}`} style={{ "--anim-delay": "80ms" } as React.CSSProperties}>
          {TITLE[audience]}
        </h2>

        <div className={s.hiwV3Layout}>
          <div className={s.hiwV3Tabs} role="tablist" aria-label="How Mitra works">
            {steps.map(({ num, Icon, title }, i) => {
              const isActive = i === activeTab;
              return (
                <button
                  key={num}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`hiw-panel-${num}`}
                  id={`hiw-tab-${num}`}
                  className={`${s.hiwV3Tab} ${isActive ? s.hiwV3TabActive : ""}`}
                  onClick={() => setActiveTab(i)}
                >
                  <span className={s.hiwV3TabNum}>{num}</span>
                  <span className={s.hiwV3TabIcon} aria-hidden="true">
                    <Icon />
                  </span>
                  <span className={s.hiwV3TabTitle}>{title}</span>
                  {isActive && inView && (
                    <span
                      key={`progress-${activeTab}-${audience}`}
                      className={s.hiwV3TabProgress}
                      aria-hidden="true"
                    />
                  )}
                </button>
              );
            })}
          </div>

          <div
            className={s.hiwV3PanelWrap}
            role="tabpanel"
            id={`hiw-panel-${steps[activeTab].num}`}
            aria-labelledby={`hiw-tab-${steps[activeTab].num}`}
          >
            <div key={`${audience}-${activeTab}`} className={s.hiwV3PanelFade}>
              <ActivePanel active={inView} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
