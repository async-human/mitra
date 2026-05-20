import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const TICKER_TEXT =
  "Placed at Razorpay  ·  Placed at Setu  ·  Placed at CRED  ·  Placed at Groww  ·  Placed at Zepto  ·  Placed at BharatPe  ·  Placed at PhonePe  ·  Placed at Slice  ·  Placed at Fi Money  ·  ";

const STATS = {
  candidate: [
    { num: "50+",    label: "Engineers placed" },
    { num: "8 days", label: "Avg. time to first interview" },
    { num: "90%+",   label: "Founder response rate" },
    { num: "₹0",     label: "Cost to candidates" },
  ],
  company: [
    { num: "50+",  label: "Successful placements" },
    { num: "8%",   label: "Success fee — half agency rate" },
    { num: "90d",  label: "Replacement guarantee" },
    { num: "Free", label: "First 2 hires" },
  ],
};

const CTA = {
  candidate: { label: "Get started — free →", href: whatsAppHrefFor("candidate") },
  company:   { label: "List a role →",         href: whatsAppHrefFor("founder") },
};

export function ProofV2({ audience }: { audience: V2Audience }) {
  const cta = CTA[audience];

  return (
    <section className={s.proof}>
      {/* Scrolling placed-at ticker */}
      <div className={s.tickerStrip} aria-hidden="true">
        <div className={s.tickerTrack}>
          <span className={s.tickerText}>{TICKER_TEXT}</span>
          <span className={s.tickerText}>{TICKER_TEXT}</span>
        </div>
      </div>

      {/* Stats + CTA */}
      <div className={`${s.proofInner} ${s.audiencePane}`} key={audience}>
        <div className={s.proofStats}>
          {STATS[audience].map((stat) => (
            <div key={stat.label}>
              <div className={s.proofStatNum}>{stat.num}</div>
              <div className={s.proofStatLabel}>{stat.label}</div>
            </div>
          ))}
        </div>
        <a
          href={cta.href}
          target="_blank"
          rel="noopener noreferrer"
          className={s.proofCta}
        >
          {cta.label}
        </a>
      </div>
    </section>
  );
}
