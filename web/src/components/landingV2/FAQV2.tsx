import { CANDIDATE_FAQ, FOUNDER_FAQ } from "@/lib/faqData";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const FAQ_BY_AUDIENCE = {
  candidate: CANDIDATE_FAQ.slice(0, 6),
  company:   FOUNDER_FAQ.slice(0, 6),
};

export function FAQV2({ audience }: { audience: V2Audience }) {
  const items = FAQ_BY_AUDIENCE[audience];

  return (
    <section className={s.sectionWrap} id="faq">
      <div className={s.sectionInner}>
        <div className={s.faqInner}>
          <p className={s.sectionLabel}>FAQ</p>
          <h2 className={s.sectionTitle}>Questions</h2>
          {items.map((item) => (
            <details key={item.id} className={s.faqItem}>
              <summary className={s.faqSummary}>
                {item.q}
                <span className={s.faqIcon} aria-hidden="true">+</span>
              </summary>
              <p className={s.faqBody}>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
