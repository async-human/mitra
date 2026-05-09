"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { BriefcaseIcon, WhatsAppIcon } from "./icons";

type Step = { title: string; desc: string; chip: string };

const CANDIDATE_STEPS: Step[] = [
  {
    title: "Chat with Mitra on WhatsApp",
    desc: "A 2-minute conversation — not a form. Your experience, what you want, what you will not compromise on.",
    chip: "2 min · WhatsApp",
  },
  {
    title: "We reason through your fit",
    desc: "Our AI evaluates trajectory, motivation, stage readiness, and culture fit — not just keywords on a resume.",
    chip: "AI reasoning · No black boxes",
  },
  {
    title: "Receive 3–5 curated matches",
    desc: "Never a list of 50. Each match includes exactly why we think it's right for you.",
    chip: "Max 5 · All explained",
  },
  {
    title: "We introduce you to the founder",
    desc: "A personal, contextual introduction — the kind a well-connected friend sends — with a 48-hour response guarantee.",
    chip: "Warm intro · 48h guarantee",
  },
];

const FOUNDER_STEPS: Step[] = [
  {
    title: "Share your hiring need",
    desc: "Send the role via WhatsApp or email. No contracts, no onboarding. We ask the five questions your JD doesn't answer.",
    chip: "24h activation",
  },
  {
    title: "We source and screen deeply",
    desc: "Our AI runs the full intake — evaluating intent, trajectory, and cultural alignment, not just listed skills.",
    chip: "Full AI screening",
  },
  {
    title: "Receive 3–5 pre-qualified intros",
    desc: "Profile, match rationale, salary expectation, notice period, and why they want your company specifically.",
    chip: "Full context on every intro",
  },
  {
    title: "Interview, decide, pay only when you hire",
    desc: "No upfront fees. 8% of first-year CTC when you hire. 90-day replacement guarantee included.",
    chip: "8% success fee · 90-day guarantee",
  },
];

const AUDIENCE_META = {
  candidate: {
    eyebrow: "For candidates",
    headline: "Your personal job search agent",
    sub: "Stop cold-applying. One honest conversation on WhatsApp — then Mitra handles everything from sourcing to the warm introduction.",
    steps: CANDIDATE_STEPS,
    accentClass: "how-accent--teal",
    badgeClass: "badge-c",
    cta: { label: "Start on WhatsApp — free", href: whatsAppHrefFor("candidate"), icon: <WhatsAppIcon size={15} />, cls: "how-cta-btn how-cta-btn--teal" },
  },
  founder: {
    eyebrow: "For founders",
    headline: "Your always-on talent partner",
    sub: "Stop drowning in CVs. Share the role and we deliver pre-qualified introductions with full context — motivation, salary, and why they want you.",
    steps: FOUNDER_STEPS,
    accentClass: "how-accent--amber",
    badgeClass: "badge-f",
    cta: { label: "List a role — first 2 hires free", href: whatsAppHrefFor("founder"), icon: <BriefcaseIcon size={15} />, cls: "how-cta-btn how-cta-btn--amber" },
  },
} as const;

export function HowItWorks() {
  const { audience } = useAudience();
  const meta = AUDIENCE_META[audience];

  return (
    <section className="how" id="how">
      <div className="how-inner">
        <Reveal className={`how-header ${meta.accentClass}`}>
          <div className="how-eyebrow">{meta.eyebrow}</div>
          <h2 className="how-h2">{meta.headline}</h2>
          <p className="how-sub">{meta.sub}</p>
        </Reveal>

        <Reveal className="how-steps-grid" delay={1}>
          {meta.steps.map((step, i) => (
            <div className={`how-step ${meta.accentClass}`} key={step.title}>
              <div className={`how-step-num ${meta.badgeClass}`}>0{i + 1} —</div>
              <div className="how-step-body">
                <div className="how-step-title">{step.title}</div>
                <div className="how-step-desc">{step.desc}</div>
                <span className="how-step-chip">{step.chip}</span>
              </div>
            </div>
          ))}
        </Reveal>

        <Reveal className="how-cta-row" delay={2}>
          <a href={meta.cta.href} target="_blank" rel="noopener noreferrer" className={meta.cta.cls}>
            {meta.cta.icon}
            {meta.cta.label}
          </a>
        </Reveal>
      </div>
    </section>
  );
}
