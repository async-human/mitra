import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

const STATS = [
  { num: "50+",    label: "Engineers placed" },
  { num: "8 days", label: "Avg. time to first interview" },
  { num: "3×",     label: "Response rate vs cold apply" },
  { num: "₹0",     label: "Cost to candidates" },
];

export function ProofV2() {
  return (
    <section className={s.proof}>
      <div className={s.proofInner}>
        <div className={s.proofStats}>
          {STATS.map((stat) => (
            <div key={stat.label}>
              <div className={s.proofStatNum}>{stat.num}</div>
              <div className={s.proofStatLabel}>{stat.label}</div>
            </div>
          ))}
        </div>
        <a
          href={whatsAppHrefFor("candidate")}
          target="_blank"
          rel="noopener noreferrer"
          className={s.proofCta}
        >
          Get started — free →
        </a>
      </div>
    </section>
  );
}
