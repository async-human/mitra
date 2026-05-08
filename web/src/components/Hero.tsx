"use client";

import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { ArrowDownIcon, BriefcaseIcon, WhatsAppIcon } from "./icons";
import { PhoneMockup } from "./PhoneMockup";
import { useAudience, type Audience } from "./AudienceContext";

const COPY = {
  candidate: {
    h1: (<>Stop sending CVs<br />into the void.<br /><em>Get introduced.</em></>),
    sub: "Mitra is your personal AI talent agent. A 2-minute conversation on WhatsApp — then we match you to India's best-funded startups and introduce you directly to the founder. No cold applications. No ghosting. Ever.",
    cta: { label: "Start on WhatsApp — free", icon: <WhatsAppIcon size={16} />, className: "btn-hero-p", href: whatsAppHrefFor("candidate") },
  },
  founder: {
    h1: (<>Stop drowning in CVs.<br />Get <em>the right person</em><br />introduced to you.</>),
    sub: "Mitra is your always-on talent partner. We source, screen, and introduce pre-qualified candidates who are genuinely motivated to join a company like yours — not a pile of resumes with no context.",
    cta: { label: "List a role — first 2 hires free", icon: <BriefcaseIcon size={16} />, className: "btn-hero-p teal", href: whatsAppHrefFor("founder") },
  },
} as const;

const CANDIDATE_CARDS = [
  { role: "Staff Engineer", company: "Setu", stage: "Series B · Fintech", salary: "₹42–52L", location: "Remote", score: "96% fit", color: "#1B5E5A" },
  { role: "Senior PM · Growth", company: "Razorpay", stage: "Series D · Payments", salary: "₹45–62L", location: "Hybrid · BLR", score: "92% fit", color: "#C07A28" },
  { role: "ML Engineer", company: "CRED", stage: "Late-stage · Wealth", salary: "₹48–70L", location: "Hybrid · BLR", score: "91% fit", color: "#6B4FBB" },
];

const FOUNDER_CARDS = [
  { name: "Arjun K.", title: "Staff Engineer · 6 yrs", skills: "Infra · Distributed systems · Golang", notice: "30 days", salary: "₹48L", badge: "Ready to move", color: "#1B5E5A" },
  { name: "Neha S.", title: "Senior PM · 5 yrs", skills: "Growth · Monetisation · B2C", notice: "Immediate", salary: "₹54L", badge: "3 competing offers", color: "#C07A28" },
  { name: "Rohit M.", title: "ML Engineer · 4 yrs", skills: "Risk models · Feature stores · Python", notice: "45 days", salary: "₹52L", badge: "Startup-only", color: "#6B4FBB" },
];

function CandidateRoleCard({ card, idx }: { card: typeof CANDIDATE_CARDS[0]; idx: number }) {
  return (
    <div className="hero-role-card" style={{ animationDelay: `${0.6 + idx * 0.15}s` }}>
      <div className="hrc-top">
        <div className="hrc-role">{card.role}</div>
        <div className="hrc-score">{card.score}</div>
      </div>
      <div className="hrc-company">
        <span className="hrc-dot" style={{ background: card.color }} />
        {card.company}
        <span className="hrc-stage">{card.stage}</span>
      </div>
      <div className="hrc-tags">
        <span className="hrc-tag hrc-tag--salary">{card.salary}</span>
        <span className="hrc-tag">{card.location}</span>
      </div>
    </div>
  );
}

function FounderCandidateCard({ card, idx }: { card: typeof FOUNDER_CARDS[0]; idx: number }) {
  return (
    <div className="hero-role-card" style={{ animationDelay: `${0.6 + idx * 0.15}s` }}>
      <div className="hrc-top">
        <div className="hrc-role">{card.name}</div>
        <div className="hrc-badge" style={{ background: `${card.color}18`, color: card.color }}>{card.badge}</div>
      </div>
      <div className="hrc-company">
        <span className="hrc-dot" style={{ background: card.color }} />
        {card.title}
      </div>
      <div className="hrc-skills">{card.skills}</div>
      <div className="hrc-tags">
        <span className="hrc-tag hrc-tag--salary">{card.salary}</span>
        <span className="hrc-tag">Notice: {card.notice}</span>
      </div>
    </div>
  );
}

export function Hero() {
  const { audience, setAudience } = useAudience();
  const copy = COPY[audience];

  return (
    <section className="hero">
      <div className="hero-left">
        <div className="aud-tog" role="tablist" aria-label="I am a">
          <button type="button" role="tab" aria-selected={audience === "candidate"} className={`tog-btn${audience === "candidate" ? " on" : ""}`} onClick={() => setAudience("candidate")}>
            I&apos;m looking for a role
          </button>
          <button type="button" role="tab" aria-selected={audience === "founder"} className={`tog-btn${audience === "founder" ? " on" : ""}`} onClick={() => setAudience("founder")}>
            I&apos;m hiring
          </button>
        </div>

        <h1 className="hero-h1">{copy.h1}</h1>
        <p className="hero-sub">{copy.sub}</p>

        <div className="hero-ctas">
          <a href={copy.cta.href} target="_blank" rel="noopener noreferrer" className={copy.cta.className}>
            {copy.cta.icon}
            {copy.cta.label}
          </a>
          <Link href="#how" className="btn-hero-s">
            See how it works
            <ArrowDownIcon size={14} />
          </Link>
        </div>

        <div className="hero-proof">
          {audience === "candidate" ? (
            <>
              <div className="proof-item"><span className="proof-dot" />Free for candidates, always</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />Avg. 8 days to first interview</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />Zero ghosting — guaranteed</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />Pan-India — remote &amp; hybrid</div>
            </>
          ) : (
            <>
              <div className="proof-item"><span className="proof-dot" />First 2 hires free</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />3–5 pre-qualified intros / week</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />8% — half agency rate</div>
              <span className="proof-sep" />
              <div className="proof-item"><span className="proof-dot" />Live in 24 hours</div>
            </>
          )}
        </div>
      </div>

      <div className="hero-right" aria-hidden="true">
        <div className="hero-right-inner">
          <div className="hero-phone-col">
            <PhoneMockup layout="hero" />
          </div>
          <div className="hero-cards-col">
            <div className="hero-cards-label">
              {audience === "candidate" ? "Live on Mitra" : "Recent intros sent"}
            </div>
            {audience === "candidate"
              ? CANDIDATE_CARDS.map((card, i) => <CandidateRoleCard key={card.company} card={card} idx={i} />)
              : FOUNDER_CARDS.map((card, i) => <FounderCandidateCard key={card.name} card={card} idx={i} />)
            }
          </div>
        </div>
      </div>
    </section>
  );
}
