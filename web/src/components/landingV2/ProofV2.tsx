import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

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
