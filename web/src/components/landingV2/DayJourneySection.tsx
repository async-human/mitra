"use client";

import { Fragment, useEffect, useRef, useState } from "react";
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

/* ── Mockup: WhatsApp-style chat ────────────────────────────── */
function ChatMockup() {
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
      </div>
    </div>
  );
}

/* ── Mockup: Match notification card ───────────────────────── */
function MatchMockup() {
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
          <div className={s.djMockupFitBar}><div className={s.djMockupFitFill} /></div>
          <span className={s.djMockupFitLabel}>94% fit</span>
        </div>
      </div>
    </div>
  );
}

/* ── Mockup: Founder reply + confirmed ─────────────────────── */
function ReplyMockup() {
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

/* ── Card data ──────────────────────────────────────────────── */

const CARDS = {
  candidate: [
    { day: "MON", title: "Brief Mitra", Mockup: ChatMockup },
    { day: "WED", title: "Your profile goes out", Mockup: MatchMockup },
    { day: "THU", title: "Founder replies", Mockup: ReplyMockup },
  ],
  company: [
    { day: "MON", title: "Post the role", Mockup: ChatMockup },
    { day: "WED", title: "Candidates scored", Mockup: MatchMockup },
    { day: "THU", title: "First intro arrives", Mockup: ReplyMockup },
  ],
};

const TITLE = {
  candidate: "Three days to your first conversation.",
  company: "Brief to first intro in 48 hours.",
};

/* ── Component ──────────────────────────────────────────────── */

export function DayJourneySection({ audience }: { audience: V2Audience }) {
  const cards = CARDS[audience];

  return (
    <section className={s.djSection}>
      <div className={s.djInner} key={audience}>
        <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
          What to expect
        </p>
        <h2 className={`${s.sectionTitle} ${s.fadeUp}`} style={{ "--anim-delay": "80ms" } as React.CSSProperties}>
          {TITLE[audience]}
        </h2>

        <div className={s.djCards}>
          {cards.map(({ day, title, Mockup }, i) => (
            <Fragment key={day}>
              <RevealCard delay={i * 130}>
                <div className={s.djCard}>
                  <div className={s.djCardTop}>
                    <span className={s.djDay}>{day}</span>
                    <p className={s.djTitle}>{title}</p>
                  </div>
                  <Mockup />
                </div>
              </RevealCard>
              {i < cards.length - 1 && (
                <div className={s.djConnector} aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}
