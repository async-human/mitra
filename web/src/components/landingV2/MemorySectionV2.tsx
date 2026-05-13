"use client";

import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const CONTENT = {
  candidate: {
    label: "Memory",
    title: "Most tools see your CV.\nMitra builds your profile.",
    left: {
      heading: "What a recruiter sees",
      items: [
        "Job title and company name",
        "Years of experience",
        "Tech stack from your CV",
        "Current salary",
      ],
    },
    right: {
      heading: "What Mitra builds",
      items: [
        "Where you're actually headed — not just where you've been",
        "The environment you thrive in vs what drains you",
        "Whether your salary expectation shifted after hearing the market",
        "That you turned down a fintech role because of the sector, not the package",
        "How fast you make decisions and how you communicate under pressure",
        "What you're really optimising for in your next move",
      ],
    },
  },
  company: {
    label: "Memory",
    title: "Most tools track candidates.\nMitra learns how you hire.",
    left: {
      heading: "What a recruiter tracks",
      items: [
        "Candidates submitted",
        "Interviews scheduled",
        "JD requirements on file",
        "Pipeline stage",
      ],
    },
    right: {
      heading: "What Mitra learns",
      items: [
        "You respond fastest to engineers with strong startup-first backgrounds",
        "You consistently pass on FAANG pedigree without ownership evidence",
        "You value first-principles thinking over years of experience",
        "Your real notice-period tolerance is 45 days, not 30",
        "What your past successful hires had in common — and what they didn't",
      ],
    },
  },
};

export function MemorySectionV2({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const titleLines = c.title.split("\n");

  return (
    <section className={s.sectionWrap}>
      <div className={s.sectionInner} key={audience}>
        <p className={`${s.sectionLabel} ${s.fadeUp}`} style={{ "--anim-delay": "0ms" } as React.CSSProperties}>
          {c.label}
        </p>
        <h2 className={`${s.memoryTitle} ${s.fadeUp}`} style={{ "--anim-delay": "80ms" } as React.CSSProperties}>
          {titleLines[0]}
          {titleLines[1] && <><br /><span className={s.memoryTitleAccent}>{titleLines[1]}</span></>}
        </h2>

        <div
          className={`${s.memoryCard} ${s.fadeUp}`}
          style={{ "--anim-delay": "180ms" } as React.CSSProperties}
        >
          {/* Left — what a recruiter/tracker sees */}
          <div className={s.memoryColLeft}>
            <p className={s.memoryColLabel}>{c.left.heading}</p>
            <ul className={s.memoryList}>
              {c.left.items.map((item, i) => (
                <li
                  key={item}
                  className={`${s.memoryItem} ${s.memoryItemMuted} ${s.memoryItemStagger}`}
                  style={{ "--item-delay": `${260 + i * 65}ms` } as React.CSSProperties}
                >
                  <span className={s.memoryItemDash} aria-hidden="true">—</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Right — what Mitra builds/learns */}
          <div className={s.memoryColRight}>
            <p className={`${s.memoryColLabel} ${s.memoryColLabelAccent}`}>{c.right.heading}</p>
            <ul className={s.memoryList}>
              {c.right.items.map((item, i) => (
                <li
                  key={item}
                  className={`${s.memoryItem} ${s.memoryItemStagger}`}
                  style={{
                    "--item-delay": `${320 + i * 80}ms`,
                    "--dot-delay": `${i * 350}ms`,
                  } as React.CSSProperties}
                >
                  <span className={s.memoryItemDot} aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
