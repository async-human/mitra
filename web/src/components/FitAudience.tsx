import { Reveal } from "./Reveal";

export function FitAudience() {
  return (
    <section className="fit-sec" id="fit" aria-label="Who Mitra is for">
      <div className="fit-inner">
        <Reveal className="fit-head sec-intro">
          <div className="eyebrow sec-intro-eyebrow">Fit</div>
          <h2 className="sec-title sec-title--center fit-title">
            Built for India&apos;s <em>product</em> startups — and builders who want in.
          </h2>
        </Reveal>

        <div className="fit-cols">
          <Reveal className="fit-card fit-card--yes" delay={1}>
            <div className="fit-card-label">Strong fit</div>
            <ul className="fit-list">
              <li>
                Candidates targeting <strong>VC-backed product companies</strong>{" "}
                (seed–Series C) in eng, product, design, or data.
              </li>
              <li>
                Founders hiring for <strong>IC and lead roles</strong> where motivation
                and culture matter as much as the CV.
              </li>
              <li>
                Teams comfortable starting on <strong>WhatsApp</strong> and moving fast
                — no lengthy vendor onboarding.
              </li>
            </ul>
          </Reveal>

          <Reveal className="fit-card fit-card--no" delay={2}>
            <div className="fit-card-label">Not focused here (yet)</div>
            <ul className="fit-list">
              <li>
                <strong>Enterprise / MNC</strong> hiring or traditional services
                shops — Mitra screens for startup intent.
              </li>
              <li>
                Pure <strong>volume campus</strong> or contract-only ramps (we may refer
                you elsewhere).
              </li>
              <li>
                Anyone who needs <strong>only a job board</strong> — we&apos;re
                introduction-led, not a listings product.
              </li>
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
