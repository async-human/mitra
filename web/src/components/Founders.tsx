"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

const CANDIDATE_FEATURES = [
  {
    title: "A personal intro, not a CV blast",
    body: "We write the context that makes founders want to meet you — your story, motivation, and what you've built. Not a forwarded PDF.",
  },
  {
    title: "Salary negotiation included",
    body: "We know market rates. Once you have an offer, we'll tell you if you're leaving money on the table — and write the counter for you.",
  },
  {
    title: "A clear answer, always",
    body: "Every introduction ends with a yes or a no. We stay in your corner until there's a definitive outcome. No ghosting. Ever.",
  },
];

const FOUNDER_FEATURES = [
  {
    title: "Context, not CVs",
    body: "Every intro includes motivation, notice period, salary expectation, and why this candidate wants to join your company specifically.",
  },
  {
    title: "Live in 24 hours",
    body: "Share the role on WhatsApp. We ask 5 questions your JD doesn't answer — then we're moving. No contracts before work starts.",
  },
  {
    title: "Half the agency rate",
    body: "8% success fee. No retainer, no subscription, no pile of CVs without context. You pay only when you hire.",
  },
];

export function Founders() {
  const { audience } = useAudience();

  const features = audience === "candidate" ? CANDIDATE_FEATURES : FOUNDER_FEATURES;
  const heading = audience === "candidate"
    ? <>Stop competing for attention.<br />Get <em>introduced</em> directly.</>
    : <>Stop drowning in CVs.<br />Start <em>hiring on instinct.</em></>;
  const quote = audience === "candidate"
    ? { text: "Mitra told me my offer was ₹8L below market and wrote the counter-offer message for me. I walked away with ₹6L more.", attr: "Product Lead · now at Finbox" }
    : { text: "You know within 10 minutes whether someone is right. The problem is getting to that conversation. Mitra solves that.", attr: "CTO · Series B startup" };

  return (
    <section className="founders-sec" id="founders">
      <Reveal className="founders-header">
        <div className="eyebrow sec-intro-eyebrow">What Mitra does for you</div>
        <h2 className="sec-title sec-title--center">{heading}</h2>
      </Reveal>

      <div className="founders-features">
        {features.map((f, i) => (
          <Reveal key={f.title} delay={([1, 2, 3] as const)[i]} className="founders-feat">
            <div className="founders-feat-body">
              <div className="founders-feat-title">{f.title}</div>
              <p className="founders-feat-text">{f.body}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <Reveal delay={4} className="founders-quote-wrap">
        <blockquote className="founders-quote-block">
          <p className="founders-quote-text">&ldquo;{quote.text}&rdquo;</p>
          <cite className="founders-quote-attr">{quote.attr}</cite>
        </blockquote>
      </Reveal>
    </section>
  );
}
