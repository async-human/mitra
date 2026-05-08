import { Reveal } from "./Reveal";

export type FaqItem = { id: string; q: string; a: string };

export const FAQ_ITEMS: FaqItem[] = [
  {
    id: "faq-vs-recruiter",
    q: "How is Mitra different from a recruiter or an agency?",
    a: "Recruiters work for the company that pays them. Mitra works for whoever we're talking to. Candidates pay nothing — ever — and we coach them through the whole process including salary negotiation. For founders, we're closer to a fractional hiring partner than an agency: we run the AI screening, make warm introductions, and only get paid when you actually hire (8% of first-year CTC, half of what most agencies charge).",
  },
  {
    id: "faq-candidate-free",
    q: "Is it really free for candidates?",
    a: "Yes. Forever. You will never be asked for a card, a subscription, or a referral fee. We're paid by the hiring company — and only when they hire someone. If you don't get hired, nobody pays anything.",
  },
  {
    id: "faq-whatsapp-duration",
    q: "How long does the WhatsApp conversation actually take?",
    a: "About 2 minutes for the initial intake. We ask 5–6 short questions about why you're moving, what you've shipped, what you want next, and what you won't compromise on. After that, you only hear from us when there's a specific match worth your time.",
  },
  {
    id: "faq-whatsapp-data",
    q: "What happens to what I share on WhatsApp?",
    a: "Your thread is stored in Mitra's systems so we can run matching, maintain context across conversations, and keep our founders' intros accurate. We don't sell chat data or use it to train third-party models. What's shared with a founder is a deliberate summary — compensation expectations, timeline, motivation, and fit rationale — only when we've agreed with you that a specific introduction makes sense. You can ask us to delete your intake records subject to legal retention needs; engaged hiring pipelines may retain minimal records for bookkeeping.",
  },
  {
    id: "faq-replacement",
    q: "What if a hire leaves within the first 90 days?",
    a: "We replace them at no additional cost. The 90-day replacement guarantee is in writing in the engagement note — no fine print, no \"approval\" process. We've replaced 3 of the ~50 placements we've made; in every case the new candidate was sent within 14 days.",
  },
  {
    id: "faq-company-stage",
    q: "What stage of company do you work with?",
    a: "Pre-seed through Series C, all India-headquartered. We don't work with services companies, MNCs, or pure-enterprise plays — Mitra only sources for product-driven startups, because that's the kind of motivation profile we screen for. If you're outside that, we'll tell you on the first call.",
  },
  {
    id: "faq-location",
    q: "Do I need to live in a specific city to use Mitra?",
    a: "No. Mitra is built for India-wide hiring. We routinely work with candidates and teams across Hyderabad, Chennai, Pune, Delhi NCR, Mumbai, and other metros and tier-two cities—with remote and hybrid roles wherever they make sense.",
  },
  {
    id: "faq-intent-screening",
    q: "What does \"intent screening\" actually mean?",
    a: "We don't just match keywords on your CV. We have a real conversation about why you're considering a move — pay, growth, manager, scope, equity, location — and what would have to be true for you to accept. That information is then summarized into the warm intro the founder receives, so the conversation starts at the right altitude instead of \"tell me about yourself\".",
  },
  {
    id: "faq-founder-interviews",
    q: "Can founders interview candidates themselves before hiring?",
    a: "Yes — we expect you to. Mitra solves the access and screening problem, not the assessment problem. After we introduce, you run your own loop: take-home, system design, founder fit, whatever you do. We just make sure the candidates entering your loop are pre-qualified, motivated, and salary-aligned.",
  },
  {
    id: "faq-not-blasted",
    q: "How do I know the candidates haven't been blasted to 50 other companies?",
    a: "Mitra does targeted introductions, not mass distribution. A candidate is introduced to a maximum of 3 hiring partners per round, and only ones we've explicitly discussed with them. You'll always know which other founders are talking to a given candidate.",
  },
  {
    id: "faq-get-started",
    q: "How do I get started?",
    a: "Tap any \"Chat with Mitra\" or \"Start on WhatsApp\" button on this page — they'll all open WhatsApp with a pre-filled message. We'll reply within a few hours during IST business hours. Founders can also book a call directly via the same WhatsApp thread.",
  },
];

export function FAQ() {
  return (
    <section className="faq-sec" id="faq" aria-label="Frequently asked questions">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">Questions, answered</div>
        <h2 className="sec-title sec-title--center">
          Everything you&apos;d want to know
          <br />
          before you <em>start.</em>
        </h2>
        <p className="sec-intro-desc sec-intro-desc--narrow">
          Still have questions? Tap any &ldquo;Chat with Mitra&rdquo; button —
          we reply on WhatsApp within a few hours. See also{" "}
          <a href="#faq-whatsapp-data" className="sec-intro-inline-link">
            WhatsApp data &amp; privacy
          </a>
          .
        </p>
      </Reveal>

      <div className="faq-list">
        {FAQ_ITEMS.map((item, i) => (
          <details
            className="faq-item"
            key={item.id}
            id={item.id}
            open={i === 0}
          >
            <summary className="faq-q">
              <span>{item.q}</span>
              <span className="faq-icon" aria-hidden="true">
                +
              </span>
            </summary>
            <div className="faq-a">{item.a}</div>
          </details>
        ))}
      </div>
    </section>
  );
}
