"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const CONTENT = {
  candidate: {
    label: "Memory",
    title: "Most tools see your CV.",
    titleAccent: "Mitra builds your profile.",
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
    title: "Most tools track candidates.",
    titleAccent: "Mitra learns how you hire.",
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

type ContentShape = (typeof CONTENT)["candidate"];

/* ─────────────────────────────────────────────────────────────────
   Inner card — remounts cleanly whenever `key` changes so the
   typewriter always restarts from scratch.
───────────────────────────────────────────────────────────────── */
function MemoryCardContent({ c }: { c: ContentShape }) {
  const rightItems = c.right.items;
  // -1 = waiting for left items to animate in before we start typing
  const [currentItem, setCurrentItem] = useState(-1);
  const [charCounts, setCharCounts] = useState<number[]>(() =>
    rightItems.map(() => 0)
  );

  // Begin typing after left items have faded in
  useEffect(() => {
    const t = setTimeout(() => setCurrentItem(0), 720);
    return () => clearTimeout(t);
  }, []);

  // Typewriter engine — drives one character at a time
  useEffect(() => {
    if (currentItem < 0 || currentItem >= rightItems.length) return;
    const item = rightItems[currentItem];
    const typed = charCounts[currentItem];

    if (typed >= item.length) {
      // Item fully typed → short pause before next
      const t = setTimeout(() => setCurrentItem((i) => i + 1), 170);
      return () => clearTimeout(t);
    }

    // Natural-feeling variable speed: base 7 ms + rare micro-pause
    const speed = 7 + (Math.random() > 0.93 ? 70 : 0);
    const t = setTimeout(() => {
      setCharCounts((prev) => {
        const next = [...prev];
        next[currentItem] += 1;
        return next;
      });
    }, speed);
    return () => clearTimeout(t);
  }, [currentItem, charCounts, rightItems]);

  const totalItems = rightItems.length;
  const doneCount = charCounts.filter(
    (n, i) => n >= rightItems[i].length
  ).length;
  const allDone = doneCount === totalItems;
  const typingHasStarted = currentItem >= 0;

  return (
    <div className={s.memoryCard}>

      {/* ── Left: static database snapshot ── */}
      <div className={s.memoryColLeft}>
        <div className={s.memoryColHeader}>
          <span className={s.memoryColHeaderDot} />
          <span className={s.memoryColLabel}>{c.left.heading}</span>
        </div>
        <ul className={s.memoryList}>
          {c.left.items.map((item, i) => (
            <li
              key={item}
              className={`${s.memoryItem} ${s.memoryItemLeft}`}
              style={{ animationDelay: `${i * 85}ms` }}
            >
              <span className={s.memoryRowNum} aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* ── Divider with drifting accent glow ── */}
      <div className={s.memoryDivider} aria-hidden="true">
        <span className={s.memoryDividerGlow} />
      </div>

      {/* ── Right: live Mitra intelligence ── */}
      <div className={s.memoryColRight}>
        <div className={s.memoryColHeader}>
          <span className={`${s.memoryColHeaderDot} ${s.memoryColHeaderDotLive}`} />
          <span className={`${s.memoryColLabel} ${s.memoryColLabelAccent}`}>
            {c.right.heading}
          </span>
          <span
            className={`${s.memoryStatusPill} ${
              !typingHasStarted ? s.memoryStatusPillHidden : ""
            } ${allDone ? s.memoryStatusPillDone : ""}`}
          >
            {allDone ? "✓ Recorded" : `${doneCount} / ${totalItems}`}
          </span>
        </div>

        <ul className={s.memoryList}>
          {rightItems.map((item, i) => {
            const typed = charCounts[i];
            const isDone = typed >= item.length;
            const isTyping = currentItem === i;
            const isVisible = isDone || isTyping;

            return (
              <li
                key={item}
                className={`${s.memoryItem} ${s.memoryItemRight} ${
                  isVisible ? s.memoryItemVisible : ""
                } ${isDone ? s.memoryItemDone : ""}`}
              >
                <span
                  className={`${s.memoryItemDot} ${isDone ? s.memoryItemDotDone : ""}`}
                  aria-hidden="true"
                />
                <span className={s.memoryItemText}>
                  {isDone ? item : item.slice(0, typed)}
                  {isTyping && (
                    <span className={s.typingCursor} aria-hidden="true" />
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Outer section — handles scroll detection and audience replays
───────────────────────────────────────────────────────────────── */
export function MemorySectionV2({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const sectionRef = useRef<HTMLElement>(null);
  const [entered, setEntered] = useState(false);
  const [cardKey, setCardKey] = useState(0);
  const isFirstSwitch = useRef(true);

  // Fire once when section scrolls into view
  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setEntered(true);
          obs.disconnect();
        }
      },
      { threshold: 0.08 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Audience change after first mount → replay typewriter if section is visible
  useEffect(() => {
    if (isFirstSwitch.current) {
      isFirstSwitch.current = false;
      return;
    }
    if (entered) setCardKey((k) => k + 1);
  }, [audience, entered]);

  return (
    <section
      className={`${s.sectionWrap} ${s.memorySectionBody} ${entered ? s.memorySectionInView : ""}`}
      ref={sectionRef}
    >
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>{c.label}</p>

        <h2 className={s.memoryTitle}>
          <span>{c.title}</span>
          <br />
          <span className={s.memoryTitleAccent}>{c.titleAccent}</span>
        </h2>

        {/* Card only mounts after the section enters view so CSS animations always run fresh */}
        {entered && <MemoryCardContent key={cardKey} c={c} />}
      </div>
    </section>
  );
}
