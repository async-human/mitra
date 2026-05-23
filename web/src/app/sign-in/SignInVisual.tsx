import s from "./sign-in.module.css";

const COPY = {
  default: {
    line1: "Your AI talent",
    line2: "companion.",
    sub: "Candidates get warm intros. Founders get pre-qualified engineers — no job board noise.",
  },
  candidate: {
    line1: "Find the role",
    line2: "made for you.",
    sub: "Talk to Mitra once. Get introduced directly to founders who already know your story.",
  },
  founder: {
    line1: "Hire engineers who",
    line2: "actually want in.",
    sub: "Brief Mitra in two minutes. Receive intros with motivation and fit context attached.",
  },
};

export function SignInVisual({ role }: { role?: "candidate" | "founder" }) {
  const c = COPY[role ?? "default"];

  return (
    <aside className={s.visualPanel} aria-hidden="true">
      <div className={s.visualInner}>
        <div className={s.bento}>

          {/* Row 1 */}
          <div className={`${s.bentoTile} ${s.bentoChat}`}>
            <div className={s.chatBubbleIn}>What would a great role look like?</div>
            <div className={s.chatBubbleOut}>Own infra at a Series A fintech</div>
            <div className={s.chatTyping}>
              <span /><span /><span />
            </div>
          </div>
          <div className={`${s.bentoTile} ${s.bentoFit}`}>
            <span className={s.bentoFitNum}>94%</span>
            <span className={s.bentoFitLabel}>fit score</span>
          </div>

          {/* Row 2 */}
          <div className={`${s.bentoTile} ${s.bentoPattern}`} />
          <div className={`${s.bentoTile} ${s.bentoStat}`}>
            <span className={s.bentoStatNum}>8d</span>
            <span className={s.bentoStatLabel}>avg. to interview</span>
          </div>
          <div className={`${s.bentoTile} ${s.bentoFree}`}>
            <span className={s.bentoFreeTop}>Free for</span>
            <span className={s.bentoFreeWord}>candidates</span>
            <span className={s.bentoFreeTop}>always</span>
          </div>

          {/* Row 3 */}
          <div className={`${s.bentoTile} ${s.bentoLogos}`}>
            <span>Setu</span>
            <span className={s.bentoLogosDot}>·</span>
            <span>CRED</span>
            <span className={s.bentoLogosDot}>·</span>
            <span>Razorpay</span>
          </div>
          <div className={`${s.bentoTile} ${s.bentoAccent}`}>
            <span className={s.bentoAccentDot} />
            <span className={s.bentoAccentDot} />
            <span className={s.bentoAccentDot} />
          </div>

        </div>

        <div className={s.visualCopy}>
          <h2 className={s.visualTitle}>
            {c.line1}
            <br />
            <span className={s.visualTitleAccent}>{c.line2}</span>
          </h2>
          <p className={s.visualSub}>{c.sub}</p>
        </div>
      </div>
    </aside>
  );
}
