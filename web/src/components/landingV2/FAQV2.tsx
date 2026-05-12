import s from "./landing-v2.module.css";

const FAQ = [
  {
    q: "Is Mitra free for candidates?",
    a: "Yes — completely free for engineers and PMs looking for a role. We charge companies a placement fee only when a hire is made. You never pay anything, ever.",
  },
  {
    q: "How is this different from LinkedIn or Naukri?",
    a: "On LinkedIn, you apply to 200 roles and hear back from 3. On Mitra, we introduce you to founders who've been briefed on your background and are expecting your message. Our warm intro response rate is over 90% — roughly 3× the cold apply rate.",
  },
  {
    q: "What kinds of companies are on Mitra?",
    a: "India-based funded startups — mostly Series A through Series C, backed by recognisable investors (Peak XV, Accel, Blume, 3one4, Lightspeed India, Y Combinator). We don't list roles from service companies or unfunded ventures.",
  },
  {
    q: "How long does the process actually take?",
    a: "The initial conversation is 2–5 minutes on WhatsApp. Most candidates see their first introduction within 24–48 hours. Average time from first message to first interview: 8 days.",
  },
  {
    q: "What if I'm not actively looking, just exploring?",
    a: "That's fine — most of our best placements started that way. Brief Mitra, see what's out there, and decide. You're not committing to anything by starting a conversation.",
  },
  {
    q: "Can Mitra help me negotiate salary?",
    a: "Yes. Once you have an offer, share it with us. We'll benchmark it against current market rates and help you decide whether to counter and how to frame it. We've helped candidates recover an average of ₹6L+ above the initial offer.",
  },
];

export function FAQV2() {
  return (
    <section className={s.sectionWrap} id="faq">
      <div className={s.sectionInner}>
        <div className={s.faqInner}>
          <p className={s.sectionLabel}>FAQ</p>
          <h2 className={s.sectionTitle}>Questions</h2>
          {FAQ.map((item) => (
            <details key={item.q} className={s.faqItem}>
              <summary className={s.faqSummary}>
                {item.q}
                <span className={s.faqIcon} aria-hidden="true">+</span>
              </summary>
              <p className={s.faqBody}>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
