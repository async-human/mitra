import type { ReactNode } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Reveal } from "./Reveal";

type Tier = {
  tier: string;
  price: ReactNode;
  /** Fallback single note (Growth / Scale) */
  note?: string;
  /** Starter: bold lead line */
  noteLead?: string;
  noteSub?: string;
  highlighted?: boolean;
  badge?: string;
  features: { label: string; check: "g" | "a" | "w" }[];
  cta: { label: string; variant: "dk" | "am" | "lt"; href: string };
  delay?: 1 | 2 | 3 | 4;
};

const TIERS: Tier[] = [
  {
    tier: "Starter",
    price: <>Free</>,
    noteLead: "Your first two hires: ₹0.",
    noteSub:
      "Then 8% of first-year CTC per hire. Replacement guarantee (90 days) spelled out in writing for eligible roles.",
    features: [
      { label: "Pay nothing for the first 2 hires", check: "g" },
      { label: "8% success fee per hire after that", check: "g" },
      { label: "90-day replacement guarantee", check: "g" },
      { label: "Up to 2 active roles", check: "g" },
    ],
    cta: { label: "Start free", variant: "dk", href: whatsAppHrefFor("founder") },
  },
  {
    tier: "Growth",
    price: (
      <>
        <span className="pc-currency">₹</span>
        35K<span className="unit">/mo</span>
      </>
    ),
    note: "Unlimited roles · cancel anytime · no success fee",
    highlighted: true,
    badge: "Most Popular",
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
    tier: "Scale",
    price: <span className="pc-price-custom">Custom</span>,
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
  if (t.noteLead) {
    return (
      <div className="pc-note-block">
        <p className="pc-note-lead">{t.noteLead}</p>
        {t.noteSub && <p className="pc-note-sub">{t.noteSub}</p>}
      </div>
    );
  }
  if (t.note) return <div className="pc-note">{t.note}</div>;
  return null;
}

export function Pricing() {
  return (
    <section className="pricing-sec" id="pricing">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">Pricing</div>
        <h2 className="sec-title sec-title--center sec-title--mb-tight">
          Simple. <em>Honest.</em> No surprises.
        </h2>
        <p className="sec-intro-italic">
          For companies only — candidates are always completely free.
        </p>
      </Reveal>
      <div className="pricing-grid">
        {TIERS.map((t) => (
          <Reveal
            key={t.tier}
            className={`price-card${t.highlighted ? " hl" : ""}`}
            delay={t.delay}
          >
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
            <a
              href={t.cta.href}
              target="_blank"
              rel="noopener noreferrer"
              className={`pc-cta cta-${t.cta.variant}`}
            >
              {t.cta.label}
            </a>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
