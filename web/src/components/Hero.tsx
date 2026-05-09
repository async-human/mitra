"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { ArrowDownIcon, BriefcaseIcon, WhatsAppIcon } from "./icons";
import { PhoneMockup } from "./PhoneMockup";
import { useAudience } from "./AudienceContext";

const COPY = {
  candidate: {
    h1: (<>Stop sending CVs<br />into the void.<br /><em>Get introduced.</em></>),
    sub: "Mitra is your personal AI talent agent. A 2-minute conversation on WhatsApp — then we match you to India's best-funded startups and introduce you directly to the founder. No cold applications. No ghosting. Ever.",
    cta: { label: "Start on WhatsApp — free", icon: <WhatsAppIcon size={16} />, className: "btn-hero-p", href: whatsAppHrefFor("candidate") },
    badge: "Now live · Join engineers placed at Setu, CRED & Razorpay",
  },
  founder: {
    h1: (<>Stop drowning in CVs.<br />Get <em>the right person</em><br />introduced to you.</>),
    sub: "Mitra is your always-on talent partner. We source, screen, and introduce pre-qualified candidates who are genuinely motivated to join a company like yours — not a pile of resumes with no context.",
    cta: { label: "List a role — first 2 hires free", icon: <BriefcaseIcon size={16} />, className: "btn-hero-p teal", href: whatsAppHrefFor("founder") },
    badge: "Now live · First 2 hires free for early founders",
  },
} as const;

const CANDIDATE_CARDS = [
  { role: "Staff Engineer", company: "Setu", stage: "Series B · Fintech", salary: "₹42–52L", location: "Remote", score: "96% fit", color: "#5E6AD2" },
  { role: "Senior PM · Growth", company: "Razorpay", stage: "Series D · Payments", salary: "₹45–62L", location: "Hybrid · BLR", score: "92% fit", color: "#5E6AD2" },
  { role: "ML Engineer", company: "CRED", stage: "Late-stage · Wealth", salary: "₹48–70L", location: "Hybrid · BLR", score: "91% fit", color: "#5E6AD2" },
];

const FOUNDER_CARDS = [
  { name: "Arjun K.", title: "Staff Engineer · 6 yrs", skills: "Infra · Distributed systems · Golang", notice: "30 days", salary: "₹48L", badge: "Ready to move", color: "#5E6AD2" },
  { name: "Neha S.", title: "Senior PM · 5 yrs", skills: "Growth · Monetisation · B2C", notice: "Immediate", salary: "₹54L", badge: "3 competing offers", color: "#5E6AD2" },
  { name: "Rohit M.", title: "ML Engineer · 4 yrs", skills: "Risk models · Feature stores · Python", notice: "45 days", salary: "₹52L", badge: "Startup-only", color: "#5E6AD2" },
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
  const heroRef = useRef<HTMLElement | null>(null);
  const [motionEnabled, setMotionEnabled] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setMotionEnabled(!media.matches && window.innerWidth > 900);
    updateMotion();
    media.addEventListener("change", updateMotion);
    window.addEventListener("resize", updateMotion);
    return () => {
      media.removeEventListener("change", updateMotion);
      window.removeEventListener("resize", updateMotion);
    };
  }, []);

  const handlePointerMove = (e: React.MouseEvent<HTMLElement>) => {
    if (!motionEnabled || !heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const mx = (x - 0.5) * 2;
    const my = (y - 0.5) * 2;
    heroRef.current.style.setProperty("--mx", mx.toFixed(3));
    heroRef.current.style.setProperty("--my", my.toFixed(3));
  };

  const handlePointerLeave = () => {
    if (!heroRef.current) return;
    heroRef.current.style.setProperty("--mx", "0");
    heroRef.current.style.setProperty("--my", "0");
  };

  return (
    <section
      ref={heroRef}
      className={`hero${motionEnabled ? " hero--motion" : ""}`}
      onMouseMove={handlePointerMove}
      onMouseLeave={handlePointerLeave}
    >
      <div className="hero-left">
        <div className="aud-tog" role="tablist" aria-label="I am a">
          <button type="button" role="tab" aria-selected={audience === "candidate"} className={`tog-btn${audience === "candidate" ? " on" : ""}`} onClick={() => setAudience("candidate")}>
            I&apos;m looking for a role
          </button>
          <button type="button" role="tab" aria-selected={audience === "founder"} className={`tog-btn${audience === "founder" ? " on" : ""}`} onClick={() => setAudience("founder")}>
            I&apos;m hiring
          </button>
        </div>

        <div key={audience} className="hero-copy">
          <a href="#stories" className="hero-badge">
            <span className="hero-badge-dot" />
            {copy.badge}
            <span className="hero-badge-arrow">→</span>
          </a>

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
