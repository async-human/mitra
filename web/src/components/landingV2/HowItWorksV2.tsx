import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

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

const STEPS = {
  candidate: [
    {
      num: "Step 01",
      Icon: IconChat,
      title: "Brief Mitra in 2 minutes",
      body: "Tell us what you actually want — not just your CV. A short WhatsApp conversation covers your motivation, what you want to own next, and what would make you say yes without sleeping on it.",
    },
    {
      num: "Step 02",
      Icon: IconSearch,
      title: "We find roles with genuine fit",
      body: "Mitra searches funded startups and ranks them against your real preferences, not keywords. You see only roles where there's a strong match — scored by how well they fit what you actually described.",
    },
    {
      num: "Step 03",
      Icon: IconArrow,
      title: "You get introduced, not applied",
      body: "A warm introduction from Mitra lands in the founder's inbox — not a cold application in a pile. They know who you are, why you fit, and why they should respond. Our intro response rate is over 90%.",
    },
  ],
  company: [
    {
      num: "Step 01",
      Icon: IconDoc,
      title: "Brief us on the role",
      body: "Tell us what the role actually needs — not just the JD, but what good looks like in 90 days, what someone needs to thrive on your team, and what you won't compromise on.",
    },
    {
      num: "Step 02",
      Icon: IconUsers,
      title: "We find candidates with intent",
      body: "Mitra speaks with engineers daily and filters for people who are motivated to join a company like yours — not just 'open to opportunities'. Every candidate is screened for motivation, stage fit, and technical background.",
    },
    {
      num: "Step 03",
      Icon: IconCheck,
      title: "You get warm introductions",
      body: "A shortlist of 3–5 pre-qualified candidates, each with full context: motivation, timeline, salary expectation, and why they want to specifically join your company. Not CVs — introductions.",
    },
  ],
};

const TITLE = {
  candidate: "From conversation to introduction in under 48 hours.",
  company: "From brief to shortlist in under a week.",
};

export function HowItWorksV2({ audience }: { audience: V2Audience }) {
  return (
    <section className={s.sectionWrap} id="how-it-works">
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>How it works</p>
        <h2 className={s.sectionTitle}>{TITLE[audience]}</h2>
        <div className={s.hiwSteps}>
          {STEPS[audience].map(({ num, Icon, title, body }) => (
            <div key={num} className={s.hiwStep}>
              <p className={s.hiwStepNum}>{num}</p>
              <div className={s.hiwStepIcon} aria-hidden="true">
                <Icon />
              </div>
              <h3 className={s.hiwStepTitle}>{title}</h3>
              <p className={s.hiwStepBody}>{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
