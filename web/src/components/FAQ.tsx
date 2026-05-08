"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";
import { CANDIDATE_FAQ, FOUNDER_FAQ } from "@/lib/faqData";

export { FAQ_ITEMS } from "@/lib/faqData";

export function FAQ() {
  const { audience } = useAudience();
  const items = audience === "candidate" ? CANDIDATE_FAQ : FOUNDER_FAQ;
  const heading = audience === "candidate"
    ? <>Everything you&apos;d want to know<br />before you <em>start.</em></>
    : <>Questions founders ask<br />before they <em>get started.</em></>;

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
