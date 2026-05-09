"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

const CONTENT = {
  candidate: {
    title: <>Built for builders who want <em>ownership</em>, not just employment.</>,
    yes: {
      label: "Strong fit",
      items: [
        <>Mid-to-senior engineers, PMs, designers, and data folks targeting <strong>VC-backed product startups</strong> (seed–Series C).</>,
        <>You want to <strong>own outcomes</strong>, not just execute tickets — you're done with large-company bureaucracy.</>,
        <>Comfortable on <strong>WhatsApp</strong> and ready to move fast when the right intro lands.</>,
        <>Willing to share your <strong>real motivation</strong> — not just a sanitised CV version of yourself.</>,
      ],
    },
    no: {
      label: "Not focused here (yet)",
      items: [
        <><strong>Freshers</strong> or campus grads — we screen for demonstrated ownership, which takes time to build.</>,
        <>Anyone targeting <strong>MNCs, services companies</strong>, or large enterprises — we only work with product-driven startups.</>,
        <>Candidates who want a <strong>passive job board</strong> — Mitra is introduction-led, not a listing product.</>,
      ],
    },
  },
  founder: {
    title: <>Built for funded startups that hire <em>on ownership</em>, not job titles.</>,
    yes: {
      label: "Strong fit",
      items: [
        <>Seed through Series C <strong>product-driven startups</strong> in India, hiring for IC or lead roles in eng, product, design, or data.</>,
        <>Teams where <strong>motivation and culture fit</strong> matter as much as the resume — you've been burned by keyword hires.</>,
        <>Founders comfortable starting on <strong>WhatsApp</strong> with no vendor onboarding — we're live in 24 hours.</>,
        <>Companies willing to <strong>pay on success</strong> — 8% only when you hire, zero upfront.</>,
      ],
    },
    no: {
      label: "Not focused here (yet)",
      items: [
        <><strong>Enterprise / MNC</strong> hiring, services shops, or companies building traditional IT products — we screen for startup intent.</>,
        <>Pure <strong>volume campus</strong> or contractor ramps — Mitra is an introduction product, not a headcount pipeline.</>,
        <>Anyone who needs <strong>only a job board</strong> or wants to manage sourcing themselves — we're a fully managed partner.</>,
      ],
    },
  },
};

export function FitAudience() {
  const { audience } = useAudience();
  const copy = CONTENT[audience];

  return (
    <section className="fit-sec" id="fit" aria-label="Who Mitra is for">
      <div className="fit-inner">
        <Reveal className="fit-head sec-intro">
          <div className="eyebrow sec-intro-eyebrow">Fit</div>
          <h2 className="sec-title sec-title--center fit-title">{copy.title}</h2>
        </Reveal>

        <div className="fit-cols">
          <Reveal className="fit-card fit-card--yes" delay={1}>
            <div className="fit-card-label">{copy.yes.label}</div>
            <ul className="fit-list">
              {copy.yes.items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </Reveal>

          <Reveal className="fit-card fit-card--no" delay={2}>
            <div className="fit-card-label">{copy.no.label}</div>
            <ul className="fit-list">
              {copy.no.items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
