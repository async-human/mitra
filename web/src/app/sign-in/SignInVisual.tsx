import s from "./sign-in.module.css";

const COPY = {
  default: {
    title: "Your AI talent companion.",
    sub: "Candidates get warm intros. Founders get pre-qualified engineers.",
  },
  candidate: {
    title: "Find the role made for you.",
    sub: "Talk to Mitra once. Get introduced directly to founders who already know your story.",
  },
  founder: {
    title: "Hire engineers who actually want in.",
    sub: "Brief Mitra in two minutes. Receive intros with fit context attached.",
  },
};

function StarShape() {
  return (
    <svg className={s.tStar} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <line x1="20" y1="3" x2="20" y2="37" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
      <line x1="3" y1="20" x2="37" y2="20" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
      <line x1="6.5" y1="6.5" x2="33.5" y2="33.5" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
      <line x1="33.5" y1="6.5" x2="6.5" y2="33.5" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
    </svg>
  );
}

function AbstractAccents() {
  return (
    <>
      <span className={`${s.absShape} ${s.absRing}`} />
      <span className={`${s.absShape} ${s.absRingSm}`} />
      <span className={`${s.absShape} ${s.absDots}`}>
        <span /><span /><span /><span />
      </span>
      <span className={`${s.absShape} ${s.absArc}`} />
      <span className={`${s.absShape} ${s.absPill}`} />
      <span className={`${s.absShape} ${s.absCross}`} />
      <span className={`${s.absShape} ${s.absBlob}`} />
      <span className={`${s.absShape} ${s.absBar}`} />
      <span className={`${s.absShape} ${s.absDiamond}`} />
    </>
  );
}

export function SignInVisual({ role }: { role?: "candidate" | "founder" }) {
  const c = COPY[role ?? "default"];

  return (
    <aside className={s.visualPanel} aria-hidden="true">
      <div className={s.visualCanvas}>
        <AbstractAccents />

        <div className={s.visualComposition}>
          <div className={s.mosaic}>
            <div className={`${s.tile} ${s.tOrange}`} />
            <div className={`${s.tile} ${s.tCream}`}>
              <div className={s.tBars}>
                <span /><span /><span />
              </div>
            </div>
            <div className={`${s.tile} ${s.tDark}`}>
              <div className={s.tGrid}>
                <span /><span /><span /><span />
              </div>
            </div>

            <div className={`${s.tile} ${s.tPeach}`}>
              <div className={s.tCircle} />
            </div>
            <div className={`${s.tile} ${s.tDark}`}>
              <div className={s.tWave} />
            </div>
            <div className={`${s.tile} ${s.tOrangeAlt}`}>
              <div className={s.tHalf} />
            </div>

            <div className={`${s.tile} ${s.tCream}`}>
              <div className={s.tBracket} />
            </div>
            <div className={`${s.tile} ${s.tOrange}`}>
              <StarShape />
            </div>
            <div className={`${s.tile} ${s.tPeach}`}>
              <div className={s.tRingFill} />
            </div>
          </div>

          <div className={s.visualCopy}>
            <h2 className={s.visualTitle}>
              {c.title.split(" ").slice(0, -1).join(" ")}{" "}
              <span className={s.visualTitleAccent}>
                {c.title.split(" ").slice(-1)[0]}
              </span>
            </h2>
            <p className={s.visualSub}>{c.sub}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
