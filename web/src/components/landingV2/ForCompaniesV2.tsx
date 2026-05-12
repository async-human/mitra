import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

export function ForCompaniesV2() {
  return (
    <section className={s.sectionWrap} id="for-companies">
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>For companies</p>
        <h2 className={s.sectionTitle}>
          Hire engineers others can&apos;t reach.
        </h2>
        <p style={{ fontSize: "1rem", color: "var(--ink2)", lineHeight: 1.72, maxWidth: 560, marginBottom: "2.5rem" }}>
          Mitra speaks with engineers every day and understands them beyond their CV.
          You get a shortlist of candidates who are genuinely interested, already qualified,
          and ready for a direct introduction — not a pipeline to manage.
        </p>
        <div className={s.hiwSteps}>
          <div className={s.hiwStep}>
            <p className={s.hiwStepNum}>For founders</p>
            <h3 className={s.hiwStepTitle}>First 2 hires free</h3>
            <p className={s.hiwStepBody}>
              No retainers, no subscriptions. Brief us on WhatsApp and we send the
              first warm introductions within 5–7 days. 8% success fee — half the
              industry rate.
            </p>
          </div>
          <div className={s.hiwStep}>
            <p className={s.hiwStepNum}>Quality bar</p>
            <h3 className={s.hiwStepTitle}>Pre-screened intent, not CVs</h3>
            <p className={s.hiwStepBody}>
              Every candidate is vetted for motivation, stage fit, and technical
              background before you ever see their name. You meet people who want
              to join your specific company — not everyone who applied.
            </p>
          </div>
          <div className={s.hiwStep}>
            <p className={s.hiwStepNum}>Guarantee</p>
            <h3 className={s.hiwStepTitle}>90-day replacement, in writing</h3>
            <p className={s.hiwStepBody}>
              If a placed candidate leaves within 90 days, we replace them at no
              cost. No approval process, no fine print. We&apos;ve replaced 3 of ~50
              placements; new candidate sent within 14 days each time.
            </p>
          </div>
        </div>
        <div style={{ marginTop: "2.5rem" }}>
          <a
            href={whatsAppHrefFor("founder")}
            target="_blank"
            rel="noopener noreferrer"
            className={s.heroPrimaryCta}
          >
            List a role — first 2 hires free
          </a>
        </div>
      </div>
    </section>
  );
}
