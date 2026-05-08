import { Reveal } from "./Reveal";

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

function Track({
  steps,
  forLabel,
  tagline,
  badgeClass,
  headClass,
}: {
  steps: Step[];
  forLabel: string;
  tagline: string;
  badgeClass: "badge-c" | "badge-f";
  headClass: "track-head--c" | "track-head--f";
}) {
  return (
    <div className="how-track">
      <div className={`track-head ${headClass}`}>
        <div className="track-for">{forLabel}</div>
        <div className="track-tagline">{tagline}</div>
      </div>
      <div className="track-steps">
        {steps.map((step, i) => (
          <div className="track-step" key={step.title}>
            <div className={`step-badge ${badgeClass}`}>{i + 1}</div>
            <div>
              <div className="step-title">{step.title}</div>
              <div className="step-desc">{step.desc}</div>
              <span className="step-chip">{step.chip}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section className="how" id="how">
      <Reveal className="eyebrow">How it works</Reveal>
      <Reveal as="h2" className="sec-title" delay={1}>
        Two paths. One agent.
        <br />
        <em>Real introductions.</em>
      </Reveal>
      <Reveal as="p" className="sec-sub" delay={2}>
        Whether you&apos;re a candidate or a founder, Mitra works on your
        behalf — not as a platform, but as a partner.
      </Reveal>
      <Reveal className="how-tracks" delay={3}>
        <Track
          steps={CANDIDATE_STEPS}
          forLabel="For candidates"
          tagline="Your personal job search agent"
          badgeClass="badge-c"
          headClass="track-head--c"
        />
        <Track
          steps={FOUNDER_STEPS}
          forLabel="For founders"
          tagline="Your always-on talent partner"
          badgeClass="badge-f"
          headClass="track-head--f"
        />
      </Reveal>
    </section>
  );
}
