"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

export type FaqItem = { id: string; q: string; a: string };

const CANDIDATE_FAQ: FaqItem[] = [
  { id: "cfaq-free", q: "Is it really free for candidates?", a: "Yes. Forever. You will never be asked for a card, a subscription, or a referral fee. Mitra is paid by the company that hires you — and only when they actually hire someone. If you don't get hired, nobody pays anything." },
  { id: "cfaq-how-long", q: "How long does the WhatsApp conversation actually take?", a: "About 2 minutes for the initial intake. We ask 5–6 short questions about why you're moving, what you've built or shipped, what you want next, and what you won't compromise on. After that, you only hear from us when there's a specific match worth your time." },
  { id: "cfaq-vs-recruiter", q: "How is Mitra different from a recruiter?", a: "Recruiters work for the company paying them — they're incentivised to close you, not serve you. Mitra works for you as a candidate: we tell you if an offer is below market, we write your counter-offer, and we coach you through the whole process. We also get paid by the company, but our model only works if you're actually happy with where you land." },
  { id: "cfaq-matching", q: "How does matching actually work?", a: "We don't keyword-match your CV against JDs. We have a real conversation about why you're considering a move, what ownership looks like in your ideal role, and what would have to be true for you to join a specific company. That context is what drives our matches — and it's what makes the introduction meaningful to the founder on the other side." },
  { id: "cfaq-ghosting", q: "What's the 'zero ghosting' guarantee?", a: "Every introduction Mitra makes will result in a clear outcome: either a response from the founder, or we will follow up on your behalf until we have one. We don't consider a conversation closed until you have a yes or no. In practice, our warm intro response rate is over 90%." },
  { id: "cfaq-salary", q: "Can Mitra really help me negotiate salary?", a: "Yes. Once you have an offer, share it with us. We'll benchmark it against current market rates and help you decide whether to counter and how to frame it. We've helped candidates recover an average of ₹6L+ above the initial offer. We write the counter-offer message if you want us to." },
  { id: "cfaq-data", q: "What happens to what I share on WhatsApp?", a: "Your thread is stored in Mitra's systems to run matching and maintain context. We don't sell chat data or use it to train third-party models. What's shared with a founder is a deliberate summary — compensation expectations, timeline, motivation, and fit rationale — only when we've agreed with you that a specific introduction makes sense. You can ask us to delete your records subject to legal retention needs." },
  { id: "cfaq-location", q: "Do I need to live in a specific city?", a: "No. Mitra works India-wide. We regularly place candidates in Hyderabad, Chennai, Pune, Delhi NCR, Mumbai, Bengaluru, and other metros — with remote and hybrid roles wherever they make sense." },
];

const FOUNDER_FAQ: FaqItem[] = [
  { id: "ffaq-cost", q: "What does it actually cost?", a: "Your first two hires are completely free. After that, it's 8% of the candidate's first-year CTC, paid only when you hire. No retainers, no subscriptions, no upfront fees. The Growth plan (₹35K/mo) removes the per-hire fee entirely and gives you unlimited roles — better if you're hiring more than 3–4 people a year." },
  { id: "ffaq-vs-agency", q: "How is Mitra different from a recruitment agency?", a: "Agencies send you CVs and disappear. We send you introductions with full context: compensation expectation, notice period, why they want to join your specific company, and what they won't compromise on. We also run a deeper AI intake than any agency screening call — evaluating motivation and ownership signals, not just listed skills. And we charge 8% vs the industry standard of 15–20%." },
  { id: "ffaq-replacement", q: "What if a hire leaves within the first 90 days?", a: "We replace them at no additional cost. The 90-day replacement guarantee is in writing in the engagement note — no fine print, no approval process. We've replaced 3 of the ~50 placements we've made; in every case the new candidate was sent within 14 days." },
  { id: "ffaq-speed", q: "How quickly can you start?", a: "Same day or next day. Share the role on WhatsApp — we'll ask 5 questions your JD doesn't answer (why now, what ownership looks like, what you're actually trying to build), and we're moving. No contracts before work starts. We send the first introductions within 5–7 business days." },
  { id: "ffaq-stage", q: "What stage of company do you work with?", a: "Pre-seed through Series C, all India-headquartered product-driven startups. We don't work with services companies, MNCs, or pure-enterprise plays — Mitra only sources for product-driven startups because that's the motivation profile we screen for. If you're outside that, we'll tell you on the first call." },
  { id: "ffaq-blasted", q: "How do I know candidates haven't been sent to 50 other companies?", a: "Mitra does targeted introductions, not mass distribution. A candidate is introduced to a maximum of 3 hiring partners per round, and only ones we've explicitly discussed with them. You'll always know which other founders are talking to a given candidate." },
  { id: "ffaq-screening", q: "What does 'intent screening' actually mean?", a: "We have a real conversation with every candidate about why they're considering a move — pay, growth, manager, scope, equity, location — and what would have to be true for them to accept an offer. That information is then summarised into the warm intro you receive, so your first conversation starts at the right altitude." },
  { id: "ffaq-get-started", q: "How do I get started?", a: "Tap the 'List a role' button anywhere on this page — it'll open WhatsApp with a pre-filled message. We'll reply within a few hours during IST business hours. You can also just describe the role in your own words; we'll ask the follow-up questions we need." },
];

export const FAQ_ITEMS = [...CANDIDATE_FAQ, ...FOUNDER_FAQ];

export function FAQ() {
  const { audience } = useAudience();
  const items = audience === "candidate" ? CANDIDATE_FAQ : FOUNDER_FAQ;
  const heading = audience === "candidate"
    ? <><>Everything you&apos;d want to know<br />before you <em>start.</em></>  </>
    : <><>Questions founders ask<br />before they <em>get started.</em></></>;

  return (
    <section className="faq-sec" id="faq" aria-label="Frequently asked questions">
      <Reveal className="sec-intro">
        <div className="eyebrow sec-intro-eyebrow">Questions, answered</div>
        <h2 className="sec-title sec-title--center">{heading}</h2>
        <p className="sec-intro-desc sec-intro-desc--narrow">
          Still have questions? Tap any &ldquo;Chat with Mitra&rdquo; button — we reply on WhatsApp within a few hours.
        </p>
      </Reveal>

      <div className="faq-list">
        {items.map((item, i) => (
          <details className="faq-item" key={item.id} id={item.id} open={i === 0}>
            <summary className="faq-q">
              <span>{item.q}</span>
              <span className="faq-icon" aria-hidden="true">+</span>
            </summary>
            <div className="faq-a">{item.a}</div>
          </details>
        ))}
      </div>
    </section>
  );
}
