"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return (
    <div ref={ref} className={`${s.revealCard} ${visible ? s.inView : ""}`} style={{ transitionDelay: `${delay}ms`, height: "100%" }}>
      {children}
    </div>
  );
}

/* ════════════════════════════════════════
   CANDIDATE mockups
════════════════════════════════════════ */

/* Candidate MON: chat with Mitra about what they want */
function CandidateChatMockup() {
  return (
    <div className={s.djMockup}>
      <div className={s.djMockupChatHeader}>
        <div className={s.djMockupAv}>M</div>
        <div>
          <div className={s.djMockupAvName}>Mitra</div>
          <div className={s.djMockupAvSub}>online · WhatsApp</div>
        </div>
      </div>
      <div className={s.djMockupMsgs}>
        <div className={s.djMockupMsgIn}>What would a great role look like for you in 12 months?</div>
        <div className={s.djMockupMsgOut}>Own infra at a Series A fintech</div>
        <div className={s.djMockupMsgIn}>Got it — ownership, early stage. Current stack?</div>
        <div className={s.djMockupMsgOut}>Go, Kubernetes, Postgres</div>
      </div>
    </div>
  );
}

/* Candidate WED: match notification — Mitra found a role for them */
function CandidateMatchMockup() {
  return (
    <div className={s.djMockup}>
      <span className={s.djMockupBadge}>⚡ 1 new match · 94% fit</span>
      <div className={s.djMockupMatchCard}>
        <div className={s.djMockupMatchTop}>
          <div className={s.djMockupMatchLogo}>S</div>
          <div>
            <div className={s.djMockupMatchCo}>Setu · Series B · Fintech</div>
            <div className={s.djMockupMatchRole}>Senior Platform Engineer</div>
          </div>
        </div>
        <div className={s.djMockupMatchMeta}>₹42–58L · Remote-friendly</div>
        <div className={s.djMockupFitRow}>
          <div className={s.djMockupFitBar}>
          <div className={s.djMockupFitFill} style={{ "--fit-pct": "94%" } as React.CSSProperties} />
        </div>
          <span className={s.djMockupFitLabel}>94% fit</span>
        </div>
      </div>
    </div>
  );
}

/* Candidate THU: founder replies, meeting confirmed */
function CandidateReplyMockup() {
  return (
    <div className={s.djMockup}>
      <div className={s.djMockupReplyCard}>
        <div className={s.djMockupReplyTop}>
          <div className={s.djMockupAv}>R</div>
          <div>
            <div className={s.djMockupAvName}>Rahul S. · Setu</div>
            <div className={s.djMockupAvSub}>9:14 AM</div>
          </div>
        </div>
        <div className={s.djMockupReplyMsg}>
          &ldquo;This is exactly who we&rsquo;ve been looking for. Thursday at 10?&rdquo;
        </div>
      </div>
      <div className={s.djMockupConfirmed}>
        <span className={s.djMockupConfirmedDot} />
        Meeting confirmed
      </div>
    </div>
  );
}

/* ════════════════════════════════════════
   COMPANY (founder) mockups
════════════════════════════════════════ */

/* Company MON: Mitra guides founder through role brief */
function CompanyBriefMockup() {
  return (
    <div className={s.djMockup}>
      <div className={s.djMockupChatHeader}>
        <div className={s.djMockupAv}>M</div>
        <div>
          <div className={s.djMockupAvName}>Mitra</div>
          <div className={s.djMockupAvSub}>Role briefing · 2 min</div>
        </div>
      </div>
      <div className={s.djMockupMsgs}>
        <div className={s.djMockupMsgIn}>What does great look like in 90 days for this hire?</div>
        <div className={s.djMockupMsgOut}>Owns all backend infra end-to-end</div>
        <div className={s.djMockupMsgIn}>Perfect. Any must-have stack or stage experience?</div>
        <div className={s.djMockupMsgOut}>Go or Rust, ideally ex-fintech</div>
      </div>
    </div>
  );
}

/* Company WED: ranked candidate shortlist */
function CompanyCandidatesMockup() {
  const candidates = [
    { initials: "PM", name: "Priya M.", meta: "5 yrs · Razorpay infra", salary: "₹52L", fit: 94 },
    { initials: "AK", name: "Arjun K.", meta: "4 yrs · Platform · Setu", salary: "₹46L", fit: 88 },
    { initials: "NR", name: "Nisha R.", meta: "3 yrs · Backend · CRED", salary: "₹38L", fit: 76 },
  ];
  return (
    <div className={s.djMockup}>
      <div className={s.djMockupBadge}>✦ 3 candidates matched</div>
      <div className={s.djMockupCandidateList}>
        {candidates.map((c) => (
          <div key={c.initials} className={s.djMockupCandidateRow}>
            <div className={s.djMockupCandidateAv}>{c.initials}</div>
            <div className={s.djMockupCandidateInfo}>
              <div className={s.djMockupCandidateName}>{c.name} <span className={s.djMockupCandidateSalary}>{c.salary}</span></div>
              <div className={s.djMockupCandidateMeta}>{c.meta}</div>
              <div className={s.djMockupCandidateBarWrap}>
                <div className={s.djMockupCandidateBar} style={{ width: `${c.fit}%` }} />
              </div>
            </div>
            <span className={s.djMockupCandidateFit}>{c.fit}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Company THU: Mitra sends intro to founder with candidate context */
function CompanyIntroMockup() {
  return (
    <div className={s.djMockup}>
      <div className={s.djMockupChatHeader}>
        <div className={s.djMockupAv}>M</div>
        <div>
          <div className={s.djMockupAvName}>Mitra</div>
          <div className={s.djMockupAvSub}>Intro · just now</div>
        </div>
      </div>
      <div className={s.djMockupMsgs}>
        <div className={s.djMockupMsgIn}>
          Introducing Priya — 5 yrs infra at Razorpay, wants ownership at a 30–50 person fintech. Salary: ₹48–55L. She&rsquo;s expecting your message.
        </div>
      </div>
      <div className={s.djMockupIntroActions}>
        <button className={s.djMockupIntroBtn} tabIndex={-1}>Interested →</button>
        <button className={s.djMockupIntroBtnGhost} tabIndex={-1}>Pass</button>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════
   Card data — audience-specific
════════════════════════════════════════ */

const CARDS = {
  candidate: [
    { day: "MON", title: "Brief Mitra", Mockup: CandidateChatMockup },
    { day: "WED", title: "Your profile goes out", Mockup: CandidateMatchMockup },
    { day: "THU", title: "Founder replies", Mockup: CandidateReplyMockup },
  ],
  company: [
    { day: "MON", title: "Post the role", Mockup: CompanyBriefMockup },
    { day: "WED", title: "Candidates scored & ranked", Mockup: CompanyCandidatesMockup },
    { day: "THU", title: "First intro arrives", Mockup: CompanyIntroMockup },
  ],
};

const TITLE = {
  candidate: "Three days to your first conversation.",
  company: "Brief to first intro in 48 hours.",
};

/* ════════════════════════════════════════
   Component
════════════════════════════════════════ */

export function DayJourneySection({ audience }: { audience: V2Audience }) {
  const cards = CARDS[audience];

  return (
    <section className={s.djSection} aria-labelledby="dj-heading">
      <div className={s.djInner} key={audience}>
        <header className={s.djHeader}>
          <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
            What to expect
          </p>
          <h2
            id="dj-heading"
            className={`${s.sectionTitle} ${s.djSectionTitle} ${s.fadeUp}`}
            style={{ "--anim-delay": "80ms" } as React.CSSProperties}
          >
            {TITLE[audience]}
          </h2>
        </header>

        <div className={s.djTimeline} role="list">
          {cards.map(({ day, title, Mockup }, i) => (
            <RevealCard key={day} delay={i * 140}>
              <article className={s.djCard} role="listitem">
                <div className={s.djCardHead}>
                  <span className={s.djDay}>{day}</span>
                  <h3 className={s.djTitle}>{title}</h3>
                </div>
                <Mockup />
              </article>
            </RevealCard>
          ))}
        </div>
      </div>
    </section>
  );
}
