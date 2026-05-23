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
    sub: "Brief Mitra in two minutes. Receive intros with motivation and fit context attached.",
  },
};

export function SignInVisual({ role }: { role?: "candidate" | "founder" }) {
  const c = COPY[role ?? "default"];

  return (
    <aside className={s.visualPanel} aria-hidden="true">
      <div className={s.visualBlobA} />
      <div className={s.visualBlobB} />

      <div className={s.visualInner}>

        <div className={s.mockChat}>
          {/* Header */}
          <div className={s.mockHeader}>
            <div className={s.mockHeaderAvatar}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.8" strokeLinejoin="round"/>
                <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.8" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className={s.mockHeaderInfo}>
              <span className={s.mockHeaderName}>Mitra</span>
              <span className={s.mockHeaderSub}>AI Talent Agent · online</span>
            </div>
            <div className={s.mockHeaderDot} />
          </div>

          {/* Messages */}
          <div className={s.mockBody}>
            <div className={`${s.mockMsgIn} ${s.mockMsgFirst}`}>
              Hi Priya! I&apos;ve gone through your background — 5 years building payments infra at Razorpay is exactly what early-stage fintechs are after. What kind of stage and team are you open to?
            </div>

            <div className={s.mockMsgOut}>
              Series A ideally. Strong eng culture, small team.
            </div>

            <div className={s.mockMsgIn}>
              Found 3 strong matches. Top pick: Setu — infra lead role, founder responds fast, 94% fit on your profile. Want me to make the intro?
            </div>

            <div className={s.mockMatchCard}>
              <div className={s.mockMatchLeft}>
                <div className={s.mockMatchCo}>Setu</div>
                <div className={s.mockMatchRole}>Infra Lead · Series B</div>
              </div>
              <div className={s.mockMatchScore}>
                <span className={s.mockMatchPct}>94%</span>
                <span className={s.mockMatchLabel}>fit</span>
              </div>
            </div>

            <div className={s.mockActions}>
              <div className={s.mockActionYes}>Yes, send the intro →</div>
              <div className={s.mockActionGhost}>See all 3</div>
            </div>
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
    </aside>
  );
}
