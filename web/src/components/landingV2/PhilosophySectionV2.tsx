import s from "./landing-v2.module.css";

const PRINCIPLES = [
  {
    title: "Supervised before autonomous",
    body: "Mitra earns autonomy through demonstrated judgment. Every new category of action is supervised before it's automated. We tell you what the agent is doing and why.",
  },
  {
    title: "Outcomes over activity",
    body: "The only metric that matters is placements that stick. Not messages sent. Not matches shown. Not response rates. Candidates happy at 90 days. Founders who come back.",
  },
  {
    title: "Radical transparency",
    body: "We publish our roadmap. We explain how matching works. We tell candidates if a salary is below market even when it costs us the placement fee. Trust is the product.",
  },
];

export function PhilosophySectionV2() {
  return (
    <section className={s.philosophy} id="philosophy">
      <div className={s.philosophyInner}>
        <p className={s.philosophyLabel}>The product philosophy</p>

        <h2 className={s.philosophyQuote}>
          &ldquo;The professional internet deserved better infrastructure than this.&rdquo;
        </h2>

        <p className={s.philosophySub}>
          Mitra is that infrastructure. The candidate still decides whether to take
          the role. The founder still decides whether to make the offer.
          Everything between those two moments&nbsp;&mdash; the signal, the context,
          the introduction&nbsp;&mdash; that&apos;s what Mitra owns.
        </p>

        <div className={s.philosophyPrinciples}>
          {PRINCIPLES.map(p => (
            <div key={p.title} className={s.philosophyCard}>
              <h3 className={s.philosophyCardTitle}>{p.title}</h3>
              <p className={s.philosophyCardBody}>{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
