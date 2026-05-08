import { Reveal } from "./Reveal";

const HIGHLIGHT_FACTS = [
  {
    lead: "Cadence",
    text: "Every introduction follows a full intake—we know motivation, timing, and why your startup stays in the conversation.",
  },
  {
    lead: "Speed",
    text: "Share the role on WhatsApp and we're moving within a day. No contracts or onboarding decks before work begins.",
  },
  {
    lead: "Context",
    text: "Compensation reality, competing offers, and hesitation—raised carefully so conversations start honest, without keyword theatre.",
  },
] as const;

/** Left column: same materials as the page (sand/white ink)—substance, no decorative SVG. */
function FoundersHighlightCard() {
  return (
    <aside className="founders-highlight">
      <div className="founders-highlight-top">
        <div className="founders-highlight-stat">
          <span className="founders-highlight-num">3–5</span>
          <span className="founders-highlight-label">
            curated introductions weekly
          </span>
        </div>
        <p className="founders-highlight-lead">
          Intros only when both sides have agreed the conversation is worth
          having—never a CV blast or inbox dump.
        </p>
      </div>
      <ul className="founders-highlight-list">
        {HIGHLIGHT_FACTS.map((item) => (
          <li key={item.lead}>
            <span className="founders-highlight-fact">{item.lead}</span>
            <span className="founders-highlight-dash" aria-hidden>
              {" "}
              —{" "}
            </span>
            {item.text}
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function Founders() {
  return (
    <section className="founders-sec" id="founders">
      <div className="founders-inner">
        <Reveal>
          <FoundersHighlightCard />
        </Reveal>

        <Reveal className="founders-content" delay={2}>
          <div className="eyebrow">Startups &amp; talent</div>
          <p className="founders-eyebrow-sub">
            Job-seekers get coaching in the same thread where hiring teams receive
            introductions—<strong>one standard of context</strong>, not two
            disconnected funnels.
          </p>
          <h2 className="sec-title founders-sec-title">
            Hire on instinct,
            <br />
            not <em>keyword filters.</em>
          </h2>
          <blockquote className="founders-quote">
            &ldquo;You know within 10 minutes whether someone is right. The
            problem is getting to that conversation.&rdquo;
          </blockquote>
          <p className="founders-body founders-body--flush">
            Mitra solves the <strong>access problem</strong> on both sides:
            serious candidates move toward the right curated startups instead of
            blasting CVs; hiring teams get introductions with enough depth for a
            decisive first conversation.
          </p>
          <p className="founders-body">
            We only work with <strong>funded, curated startups</strong>—no
            enterprise theatre. Builders on both sides of the hire, with
            expectations aligned before anyone meets.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
