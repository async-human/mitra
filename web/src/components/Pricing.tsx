"use client";

import type { ReactNode } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

const CANDIDATE_PERKS = [
  "2-minute WhatsApp intake — no forms, no accounts",
  "3–5 curated matches with written rationale",
  "Personal warm introduction to the founder",
  "Salary benchmarking and negotiation coaching",
  "48-hour response guarantee on every intro",
  "Coaching through the full interview process",
];

type Tier = {
  tier: string; price: ReactNode; noteLead?: string; noteSub?: string; note?: string;
  highlighted?: boolean; badge?: string;
  features: { label: string; check: "g" | "a" | "w" }[];
  cta: { label: string; variant: "dk" | "am" | "lt"; href: string };
  delay?: 1 | 2 | 3 | 4;
};

const FOUNDER_TIERS: Tier[] = [
  {
    tier: "Starter", price: <>Free</>,
    noteLead: "Your first two hires: ₹0.",
    noteSub: "Then 8% of first-year CTC per hire. Replacement guarantee (90 days) spelled out in writing.",
    features: [
      { label: "Pay nothing for the first 2 hires", check: "g" },
      { label: "8% success fee per hire after that", check: "g" },
      { label: "90-day replacement guarantee", check: "g" },
      { label: "Up to 2 active roles", check: "g" },
    ],
    cta: { label: "Start free", variant: "dk", href: whatsAppHrefFor("founder") },
  },
  {
    tier: "Growth", price: <><span className="pc-currency">₹</span>35K<span className="unit">/mo</span></>,
    note: "Unlimited roles · cancel anytime · no success fee",
    highlighted: true, badge: "Most Popular",
    features: [
      { label: "Unlimited active roles", check: "w" },
      { label: "2× weekly matching cycles", check: "w" },
      { label: "Hiring dashboard and market intel", check: "w" },
      { label: "Full candidate context notes", check: "w" },
      { label: "Dedicated account manager", check: "w" },
    ],
    cta: { label: "Get started", variant: "am", href: whatsAppHrefFor("founder") },
    delay: 1,
  },
  {
    tier: "Scale", price: <span className="pc-price-custom">Custom</span>,
    note: "Series B+ · high-volume hiring",
    features: [
      { label: "Everything in Growth", check: "a" },
      { label: "Employer branding campaigns", check: "a" },
      { label: "Campus and fresher pipeline", check: "a" },
      { label: "ATS integration and API access", check: "a" },
    ],
    cta: { label: "Talk to us", variant: "dk", href: whatsAppHrefFor("founder") },
    delay: 2,
  },
];

function TierNote({ t }: { t: Tier }) {
  if (t.noteLead) return (
    <div className="pc-note-block">
      <p className="pc-note-lead">{t.noteLead}</p>
      {t.noteSub && <p className="pc-note-sub">{t.noteSub}</p>}
    </div>
  );
  if (t.note) return <div className="pc-note">{t.note}</div>;
  return null;
}

function CandidatePricing() {
  return (
    <section className="pricing-sec" id="pricing">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">Pricing</div>
        <h2 className="sec-title sec-title--center sec-title--mb-tight">
          For candidates: <em>always free.</em>
        </h2>
        <p className="sec-intro-italic">No card. No subscription. No referral fee. Ever.</p>
      </Reveal>

      <Reveal delay={1}>
        <div className="candidate-pricing-card">
          <div className="cprice-left">
            <div className="cprice-amount">₹0</div>
            <div className="cprice-label">Your cost to use Mitra</div>
            <p className="cprice-note">
              We're paid by the company that hires you — and only when they actually hire. If no hire happens, nobody pays anything.
            </p>
            <a href={whatsAppHrefFor("candidate")} target="_blank" rel="noopener noreferrer" className="cprice-cta">
              Start on WhatsApp — free
            </a>
          </div>
          <div className="cprice-right">
            <div className="cprice-perks-label">What you get</div>
            <ul className="cprice-perks">
              {CANDIDATE_PERKS.map((p) => (
                <li key={p}>
                  <span className="pc-chk chk-g">✓</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

export function Pricing() {
  const { audience } = useAudience();
  if (audience === "candidate") return <CandidatePricing />;

  return (
    <section className="pricing-sec" id="pricing">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">Pricing</div>
        <h2 className="sec-title sec-title--center sec-title--mb-tight">
          Simple. <em>Honest.</em> No surprises.
        </h2>
        <p className="sec-intro-italic">For companies only — candidates are always completely free.</p>
      </Reveal>
      <div className="pricing-grid">
        {FOUNDER_TIERS.map((t) => (
          <Reveal key={t.tier} className={`price-card${t.highlighted ? " hl" : ""}`} delay={t.delay}>
            {t.badge && <div className="pc-badge">{t.badge}</div>}
            <div className="pc-tier">{t.tier}</div>
            <div className="pc-price">{t.price}</div>
            <TierNote t={t} />
            <div className="pc-div" />
            {t.features.map((f) => (
              <div className="pc-feat" key={f.label}>
                <span className={`pc-chk chk-${f.check}`}>✓</span>
                {f.label}
              </div>
            ))}
            <a href={t.cta.href} target="_blank" rel="noopener noreferrer" className={`pc-cta cta-${t.cta.variant}`}>
              {t.cta.label}
            </a>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
