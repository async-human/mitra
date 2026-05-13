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
   Animated card.

   Key insight: this component is mounted with key={audience} so it
   always unmounts+remounts when audience changes — state is never
   stale relative to the `c` prop. The `key` and `c` both derive
   from `audience` in the same parent render, so they are always
   in sync (fixes the "rightItems[i] is undefined" crash).
───────────────────────────────────────────────────────────────── */
function MemoryCardContent({ c }: { c: ContentShape }) {
  const rightItems = c.right.items;
  const [currentItem, setCurrentItem] = useState(-1);
  const [charCounts, setCharCounts] = useState<number[]>(() =>
    rightItems.map(() => 0)
  );
  // Per-character counter lives in a ref — advances without triggering the effect
  const charCountRef = useRef(0);

  // Begin typing after left items have faded in
  useEffect(() => {
    const t = setTimeout(() => setCurrentItem(0), 720);
    return () => clearTimeout(t);
  }, []);

  // Typing engine — only re-runs when currentItem advances, NOT on every char
  useEffect(() => {
    if (currentItem < 0 || currentItem >= rightItems.length) return;
    const item = rightItems[currentItem];
    charCountRef.current = 0;

    const interval = setInterval(() => {
      charCountRef.current += 1;
      const n = charCountRef.current;

      setCharCounts((prev) => {
        const next = [...prev];
        next[currentItem] = n;
        return next;
      });

      if (n >= item.length) {
        clearInterval(interval);
        setTimeout(() => setCurrentItem((i) => i + 1), 160);
      }
    }, 8);

    return () => clearInterval(interval);
  }, [currentItem, rightItems]);

  const totalItems = rightItems.length;
  // Guard: charCounts length always matches rightItems length since this
  // component remounts (new key) whenever audience changes.
  const doneCount = charCounts.filter(
    (n, i) => i < rightItems.length && n >= rightItems[i].length
  ).length;
  const allDone = doneCount === totalItems;
  const typingStarted = currentItem >= 0;

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

      {/* ── Divider ── */}
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
              !typingStarted ? s.memoryStatusPillHidden : ""
            } ${allDone ? s.memoryStatusPillDone : ""}`}
          >
            {allDone ? "✓ Recorded" : `${doneCount} / ${totalItems}`}
          </span>
        </div>

        <ul className={s.memoryList}>
          {rightItems.map((item, i) => {
            const typed = charCounts[i] ?? 0;
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
                  className={`${s.memoryItemDot} ${
                    isDone ? s.memoryItemDotDone : ""
                  }`}
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
   Outer section — scroll detection only.
   key={audience} on MemoryCardContent ensures it remounts whenever
   audience changes, keeping charCounts perfectly in sync with c.
───────────────────────────────────────────────────────────────── */
export function MemorySectionV2({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const sectionRef = useRef<HTMLElement>(null);
  const [entered, setEntered] = useState(false);

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

  return (
    <section
      className={`${s.sectionWrap} ${s.memorySectionBody} ${
        entered ? s.memorySectionInView : ""
      }`}
      ref={sectionRef}
    >
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>{c.label}</p>

        <h2 className={s.memoryTitle}>
          <span>{c.title}</span>
          <br />
          <span className={s.memoryTitleAccent}>{c.titleAccent}</span>
        </h2>

        {/*
          key={audience}: when audience changes, this component unmounts and
          remounts with fresh state — charCounts always matches rightItems.
          No separate cardKey state needed.
        */}
        {entered && <MemoryCardContent key={audience} c={c} />}
      </div>
    </section>
  );
}
