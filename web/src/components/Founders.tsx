"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

const CANDIDATE_FACTS = [
  { lead: "Warm intro", text: "We write a personal introduction to the founder — not a CV blast. You show up as a human being, not an applicant number." },
  { lead: "Negotiation", text: "Once you have an offer, we help you counter. We know what market rate looks like and we'll tell you if you're being underpaid." },
  { lead: "Zero ghosting", text: "You will always get an outcome from every introduction we make. We stay in your corner until there's a clear answer." },
] as const;

const FOUNDER_FACTS = [
  { lead: "Cadence", text: "Every introduction follows a full intake — we know motivation, timing, and why your startup stays in the conversation." },
  { lead: "Speed", text: "Share the role on WhatsApp and we're moving within a day. No contracts or onboarding decks before work begins." },
  { lead: "Context", text: "Compensation reality, competing offers, and hesitation — raised carefully so conversations start honest, without keyword theatre." },
] as const;

export function Founders() {
  const { audience } = useAudience();

  if (audience === "candidate") {
    return (
      <section className="founders-sec" id="founders">
        <div className="founders-inner">
          <Reveal>
            <aside className="founders-highlight">
              <div className="founders-highlight-top">
                <div className="founders-highlight-stat">
                  <span className="founders-highlight-num">₹6L</span>
                  <span className="founders-highlight-label">average extra salary negotiated per candidate</span>
                </div>
                <p className="founders-highlight-lead">
                  Mitra doesn't just find you a job — we make sure you're paid what you're worth when you get there.
                </p>
              </div>
              <ul className="founders-highlight-list">
                {CANDIDATE_FACTS.map((item) => (
                  <li key={item.lead}>
                    <span className="founders-highlight-fact">{item.lead}</span>
                    <span className="founders-highlight-dash" aria-hidden> — </span>
                    {item.text}
                  </li>
                ))}
              </ul>
            </aside>
          </Reveal>

          <Reveal className="founders-content" delay={2}>
            <div className="eyebrow">What Mitra does for you</div>
            <p className="founders-eyebrow-sub">
              Every candidate gets the same level of attention — whether you're a Staff Engineer or a Senior PM.
            </p>
            <h2 className="sec-title founders-sec-title">
              Stop competing for attention.
              <br />
              Get <em>introduced</em> directly.
            </h2>
            <blockquote className="founders-quote">
              &ldquo;Mitra told me my offer was ₹8L below market and wrote the counter-offer message for me. I walked away with ₹6L more.&rdquo;
            </blockquote>
            <p className="founders-body founders-body--flush">
              We solve the <strong>access problem</strong>: the roles that are right for you are rarely posted publicly, and the founders who are right for you don't know you exist. Mitra bridges that gap with a personal, contextual introduction.
            </p>
            <p className="founders-body">
              We only work with <strong>funded, curated startups</strong> — no enterprise, no services shops. Every match comes with a written rationale so you know exactly why we think it's right.
            </p>
          </Reveal>
        </div>
      </section>
    );
  }

  return (
    <section className="founders-sec" id="founders">
      <div className="founders-inner">
        <Reveal>
          <aside className="founders-highlight">
            <div className="founders-highlight-top">
              <div className="founders-highlight-stat">
                <span className="founders-highlight-num">3–5</span>
                <span className="founders-highlight-label">curated introductions weekly</span>
              </div>
              <p className="founders-highlight-lead">
                Intros only when both sides have agreed the conversation is worth having — never a CV blast or inbox dump.
              </p>
            </div>
            <ul className="founders-highlight-list">
              {FOUNDER_FACTS.map((item) => (
                <li key={item.lead}>
                  <span className="founders-highlight-fact">{item.lead}</span>
                  <span className="founders-highlight-dash" aria-hidden> — </span>
                  {item.text}
                </li>
              ))}
            </ul>
          </aside>
        </Reveal>

        <Reveal className="founders-content" delay={2}>
          <div className="eyebrow">Startups &amp; talent</div>
          <p className="founders-eyebrow-sub">
            Job-seekers get coaching in the same thread where hiring teams receive introductions — <strong>one standard of context</strong>, not two disconnected funnels.
          </p>
          <h2 className="sec-title founders-sec-title">
            Hire on instinct,
            <br />
            not <em>keyword filters.</em>
          </h2>
          <blockquote className="founders-quote">
            &ldquo;You know within 10 minutes whether someone is right. The problem is getting to that conversation.&rdquo;
          </blockquote>
          <p className="founders-body founders-body--flush">
            Mitra solves the <strong>access problem</strong> on both sides: serious candidates move toward the right curated startups; hiring teams get introductions with enough depth for a decisive first conversation.
          </p>
          <p className="founders-body">
            We only work with <strong>funded, curated startups</strong> — no enterprise theatre. Builders on both sides of the hire, with expectations aligned before anyone meets.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
