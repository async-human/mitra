import s from "./landing-v2.module.css";

const STEPS = [
  {
    num: "Step 01",
    icon: "💬",
    title: "Brief Mitra in 2 minutes",
    body: "Tell us what you actually want — not just your CV. A short WhatsApp conversation covers your motivation, what you want to own next, and what would make you say yes without sleeping on it.",
  },
  {
    num: "Step 02",
    icon: "✦",
    title: "We find roles with genuine fit",
    body: "Mitra searches funded startups and ranks them against your real preferences, not keywords. You see only roles where there's a strong match — scored by how well they fit what you actually described.",
  },
  {
    num: "Step 03",
    icon: "🤝",
    title: "You get introduced, not applied",
    body: "A warm introduction from Mitra lands in the founder's inbox — not a cold application in a pile. They know who you are, why you fit, and why they should respond. Our intro response rate is over 90%.",
  },
];

export function HowItWorksV2() {
  return (
    <section className={s.sectionWrap} id="how-it-works">
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>How it works</p>
        <h2 className={s.sectionTitle}>
          From conversation to introduction in under 48 hours.
        </h2>
        <div className={s.hiwSteps}>
          {STEPS.map((step) => (
            <div key={step.num} className={s.hiwStep}>
              <p className={s.hiwStepNum}>{step.num}</p>
              <div className={s.hiwStepIcon} aria-hidden="true">{step.icon}</div>
              <h3 className={s.hiwStepTitle}>{step.title}</h3>
              <p className={s.hiwStepBody}>{step.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
